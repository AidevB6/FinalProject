import React, {useState} from "react";
import {trackPromise} from "react-promise-tracker";

import axios from "axios";

import SelectGenre from "./SelectGenre";
import SelectSongs from "./SelectSongs";

axios.defaults.withCredentials = true;
var host = '127.0.0.1'

function MakePlaylist(props) {

    const [UserData, setUserData] = useState({
        like: {
            id: 0,
            plylst_title: "",
            updt_date: "2012-09-29 01:57:26.000"
        },
        dislike: {
            id: 1,
            plylst_title: "",
            updt_date: "2012-09-29 01:57:26.000"
        }
    });

    const [ViewGenre, setViewGenre] = useState(true);
    const [ViewSongs, setViewSongs] = useState(false);

    const [Tags, setTags] = useState(null);

    const onChangeState = (LikeGenre, DislikeGenre) => {

        UserData["like"]["tags"] = LikeGenre;
        UserData["dislike"]["tags"] = DislikeGenre;

        setUserData(UserData);

        setTags(LikeGenre);

        setViewGenre(!ViewGenre);
        setViewSongs(!ViewSongs);
    };

    const onFinished = (LikeSong, DislikeSong) => {

        props.setViewPage(false);
        
        UserData["like"]["songs"] = LikeSong;
        UserData["dislike"]["songs"] = DislikeSong;

        setUserData(UserData);
        trackPromise(
            axios.post(`http://${host}:8000/playlist/recommend`, [UserData])
                .then(response => {
                    if (response.data && response.data.success) {
                        window.location.reload();
                    } else {
                        alert('데이터 전송에 실패했습니다.');
                    }
                })
                .catch(error => {
                    console.log(error);
                })
        )
    };

    return (
        <>
            {
                ViewGenre &&
                <SelectGenre onChangePage={onChangeState}/>
            }
            {
                ViewSongs && Tags &&
                <SelectSongs tags={Tags} onSubmit={onFinished}/>
            }
        </>
    );
}

export default MakePlaylist;
