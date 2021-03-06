import datetime as dt
from collections import Counter, defaultdict
from tqdm import tqdm

import numpy as np

from Utils.file import write_json
from Utils.preprocessing import DicGenerator, remove_seen, most_popular
from Utils.static import *

## 추천 함수
'''
input
 > train: 학습에 사용할 playlist들
 > questions: 일부가 가려진 question용 playlist들
 > n_msp, n_mtp, sim_measure: 하이퍼파라미터
 > song_meta: song의 meta 정보
 > save: 파일 저장 여부
output
 > questions에 대한 최종 추천 리스트
'''

## 2단계: 함수 정의
# 1) Counter 객체에서 빈도수 기준 topk개 출력
def most_similar(cnt, topk):
    cnt_topk = cnt.most_common(topk)
    return [k for k, v in cnt_topk]

# 2) 미리 계산한 유사도 기준 topk개의 플레이리스트의 plylsts와 scores 출력
def most_similar_emb(q_id, topk, emb_scores):
    plylsts = [t[0] for t in emb_scores[q_id][:topk]]
    scores = [t[1] for t in emb_scores[q_id][:topk]]

    return plylsts, scores

def calc_scores(n_msp, n_mtp, freq_song, plylst_song_dic, plylst_tag_dic, q_songs, song_plylst_C, plylsts, scores):
    plylst_song_scores = defaultdict(lambda: 0)
    plylst_tag_scores = defaultdict(lambda: 0)

    new_song_plylst_dict = defaultdict(set)
    for plylst in plylsts[0]:
        for _song in plylst_song_dic[plylst]:
            new_song_plylst_dict[_song].add(plylst)

    # 3-1. plylst_song_scores 계산
    for idx, ms_p in enumerate(plylsts[0]):
        for song in plylst_song_dic[ms_p]:
            song_score = 0
            for q_s in q_songs:
                try:
                    song_score += len(new_song_plylst_dict[q_s] & new_song_plylst_dict[song]) / len(new_song_plylst_dict[q_s])
                except:
                    pass
            if song in freq_song:
                plylst_song_scores[song] += song_plylst_C[ms_p] * song_score * scores[0][idx] * (n_msp - idx) * 4
            else:
                plylst_song_scores[song] += song_plylst_C[ms_p] * song_score * scores[0][idx] * (n_msp - idx)

        for tag in plylst_tag_dic[ms_p]:
            plylst_tag_scores[tag] += scores[1][idx] * (n_msp - idx)

    # 3-2. plylst_tag_scores 계산
    for idx, mt_p in enumerate(plylsts[1]):
        for tag in plylst_tag_dic[mt_p]:
            plylst_tag_scores[tag] += scores[1][idx] * (n_mtp - idx)

        for song in plylst_song_dic[mt_p]:
            plylst_song_scores[song] += scores[1][idx]

    # 3-3. plylst_{song/tag}_scores 보정
    for idx, mt_p in enumerate(plylsts[2]):
        for song in plylst_song_dic[ms_p] :
            plylst_song_scores[song] += scores[2][idx] * (n_msp - idx)
            
        for tag in plylst_tag_dic[mt_p] :
            plylst_tag_scores[tag] += scores[2][idx] * (n_mtp - idx)

    return plylst_song_scores, plylst_tag_scores

def inference(song_mp, tag_mp, song_issue_dic, song_artist_dic, q, tag_song_C, song_tag_status, plylst_song_scores, plylst_tag_scores):
    q_songs = q['songs']
    q_tags = q['tags']

    # 4) song과 tag 둘 다 없거나 적은 경우 예측해서 채워넣기
    if song_tag_status == 0:
        # q_songs 새롭게 채워넣기 (원래는 song가 없지만 title_scores 기준 유사한 플레이리스트로부터 song 예측)
        pre_songs = sorted(plylst_song_scores.items(), key=lambda x: x[1], reverse=True)
        pre_songs = [scores[0] for scores in pre_songs][:200]
        pre_songs = pre_songs + remove_seen(pre_songs, song_mp)
        q_songs = pre_songs[:100]

        # q_tags 새롭게 채워넣기 (원래는 tag가 없지만 title_scores 기준 유사한 플레이리스트로부터 tag 예측)
        pre_tags = sorted(plylst_tag_scores.items(), key=lambda x: x[1], reverse=True)
        pre_tags = [scores[0] for scores in pre_tags][:20]
        pre_tags = pre_tags + remove_seen(pre_tags, tag_mp)
        q_tags = pre_tags[:10]

    # 5) questions 플레이리스트에 대해 추천
    ## song 추천
    lt_song_art = []
    if len(q_songs) > 0 : # song 있을 때
        plylst_song_scores = sorted(plylst_song_scores.items(), key=lambda x: x[1], reverse=True)

        lt_artist = []
        for w_song in q_songs:
            lt_artist.extend(song_artist_dic[w_song])

        counter_artist = Counter(lt_artist)
        counter_artist = sorted(counter_artist.items(), key=lambda x: x[1], reverse=True)

        if song_tag_status == 1:
            artist = [art[0] for art in counter_artist]
        else:
            artist = [x[0] for x in counter_artist if x[1] > 1]

        cand_ms = [scores[0] for scores in plylst_song_scores][(100 - len(artist)):1000]
        for cand in cand_ms:
            if artist == []:
                break
            if cand in q_songs:
                break
            for art in song_artist_dic[cand]:
                if art in artist:
                    lt_song_art.append(cand)
                    artist.remove(art)
                    break

        song_ms = [scores[0] for scores in plylst_song_scores][:200]
    else : # song 없고, tag 있을 때
        song_ms = most_similar(tag_song_C, 200)
    
    ## tag 추천
    if len(q_tags) > 0 : # tag 있을 때
        plylst_tag_scores = sorted(plylst_tag_scores.items(), key=lambda x: x[1], reverse=True)
        tag_ms = [scores[0] for scores in plylst_tag_scores][:20]
    else : # tag 없고, song 있을 때
        plylst_tag_scores = sorted(plylst_tag_scores.items(), key=lambda x: x[1], reverse=True)
        tag_ms = [scores[0] for scores in plylst_tag_scores][:20]
        
    if q['updt_date'] : ## issue date 늦은 song 제거
        q_updt_date = q['updt_date'][:4] + q['updt_date'][5:7] + q['updt_date'][8:10]
        song_ms = [x for x in song_ms if song_issue_dic[x] < q_updt_date]

    ## 중복 제거 및 부족하면 most_popular로 채워넣기
    song_candidate = song_ms + remove_seen(song_ms, song_mp)
    tag_candidate = tag_ms + remove_seen(tag_ms, tag_mp)

    song_remove = q_songs
    tag_remove = q_tags

    song_candidate = song_candidate[:100] if song_tag_status == 0 else remove_seen(song_remove, song_candidate)[:100]
    if len(lt_song_art) > 0:
        lt_song_art = [x for x in lt_song_art if x not in song_candidate]
        song_candidate[(100 - len(lt_song_art)):100] = lt_song_art

    tag_candidate = tag_candidate[:10] if song_tag_status == 0 else remove_seen(tag_remove, tag_candidate)[:10]

    return song_candidate, tag_candidate


def Recommender(train, questions, n_msp, n_mtp, mode, song_meta, freq_song, save=False):
    ## 최종 추천리스트
    rec_list = []

    ## 1단계: 전처리
    # 1) 추천 결과가 없거나 모자란 경우를 위해 most_popular 생성
    _, song_mp = most_popular(train, "songs", 200)
    _, tag_mp = most_popular(train, "tags", 20)

    # 2) 빠른 접근을 위한 Dictionary 생성
    song_plylst_dic, song_tag_dic, plylst_song_dic, plylst_tag_dic, tag_plylst_dic, tag_song_dic, song_issue_dic, song_artist_dic = DicGenerator(train, song_meta)

    # 3) 미리 계산한 플레이리스트 유사도 불러오기
    '''
    sim_scores: 입력으로 들어온 questions과 train간 유사도 (Autoencoder 기반)
    gnr_scores: 입력으로 들어온 questions과 train간 유사도 (genre 정보 추가)
    title_scores: 입력으로 들어온 questions과 train간 유사도 (Word2vec 기반)
    '''
    sim_scores = np.load(autoencoder_score_file_path, allow_pickle=True).item()
    gnr_scores = np.load(autoencoder_gnr_score_file_path, allow_pickle=True).item()
    title_scores = np.load(word2vec_score_file_path, allow_pickle=True).item()

    ## 3단계: 입력으로 들어온 questions 플레이리스트에 대해 추천
    for q in tqdm(questions):

        # 1) question 플레이리스트의 정보
        # 수록 song/tag
        q_songs = q['songs']
        q_tags = q['tags']

        # 수록 song/tag와 함께 등장한 song/tag/plylst 빈도 수
        song_plylst_C = Counter()
        song_tag_C = Counter()
        tag_plylst_C = Counter()
        tag_song_C = Counter()

        # 2) 빈도수 기반 추천을 위해 카운트
        # 수록 song에 대해
        for q_s in q_songs:
            song_plylst_C.update(song_plylst_dic[q_s])
            song_tag_C.update(song_tag_dic[q_s])
        # 수록 tag에 대해
        for q_t in q_tags:
            tag_plylst_C.update(tag_plylst_dic[q_t])
            tag_song_C.update(tag_song_dic[q_t])
        # 수록곡 수로 나눠서 비율로 계산
        for i, j in list(song_plylst_C.items()):
            if len(plylst_song_dic[i]) > 0:
                song_plylst_C[i] = (j / len(plylst_song_dic[i]))

        # 수록 song/tag가 둘 다 없거나 적을 때
        song_tag_status = 2
        if len(q_songs) == 0 and len(q_tags) == 0:
            song_tag_status = 0
        elif len(q_songs) <= 3:
            song_tag_status = 1

        # 3) 유사도 기반 추천을 위해 점수 계산
        # Case 1: song과 tag가 둘 다 없는 경우
        if song_tag_status == 0:
            # plylst_ms / plylst_mt: title_scores 기준 유사한 플레이리스트 n_msp / n_mtp개
            plylst_ms, song_scores = most_similar_emb(q['id'], n_msp, title_scores)
            plylst_mt, tag_scores = most_similar_emb(q['id'], n_mtp, title_scores)
            plylst_add, add_scores = most_similar_emb(q['id'], n_mtp, sim_scores)

        # Case 2: song과 tag가 부족한 경우
        elif song_tag_status == 1 :
            plylst_ms, song_scores = most_similar_emb(q['id'], n_msp, sim_scores)
            plylst_mt, tag_scores = most_similar_emb(q['id'], n_mtp, title_scores)
            plylst_add, add_scores = most_similar_emb(q['id'], n_mtp, gnr_scores)

        # Case 3: song과 tag가 충분한 경우
        else:
            plylst_ms, song_scores = most_similar_emb(q['id'], n_msp, sim_scores)
            plylst_mt, tag_scores = most_similar_emb(q['id'], n_mtp, gnr_scores)
            plylst_add, add_scores = most_similar_emb(q['id'], n_mtp, title_scores)

        plylsts = [plylst_ms, plylst_mt, plylst_add]
        scores = [song_scores, tag_scores, add_scores]

        plylst_song_scores, plylst_tag_scores = calc_scores(n_msp, n_mtp, freq_song, plylst_song_dic, plylst_tag_dic, q_songs, song_plylst_C, plylsts, scores)
    
        song_candidate, tag_candidate = inference(song_mp, tag_mp, song_issue_dic, song_artist_dic, q, tag_song_C, song_tag_status, plylst_song_scores, plylst_tag_scores)
        
        rec_list.append({
            "id": q["id"],
            "songs": song_candidate,
            "tags": tag_candidate
        })

    # 6) results.json 파일 저장 여부
    if save == True:
        write_json(rec_list, 'results/results_' + dt.datetime.now().strftime("%y%m%d-%H%M%S") + '_' + mode + '.json')

    return rec_list

