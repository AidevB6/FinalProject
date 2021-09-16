/*!

=========================================================
* Argon Dashboard React - v1.2.1
=========================================================

* Product Page: https://www.creative-tim.com/product/argon-dashboard-react
* Copyright 2021 Creative Tim (https://www.creative-tim.com)
* Licensed under MIT (https://github.com/creativetimofficial/argon-dashboard-react/blob/master/LICENSE.md)

* Coded by Creative Tim

=========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

*/

import React from "react";

// reactstrap components
import {Card, CardHeader, Container} from "reactstrap";

import Header from "components/Headers/Header.js";


const Index = () => {

    return (
        <>
            <Header/>
            <Container className="mt--7" fluid>
                <Card className="shadow">
                    <CardHeader className="border-0 text-center">
                        <img alt="programmers" src="/images/mussg.gif"/>
                    </CardHeader>
                </Card>
            </Container>
        </>
    );
};

export default Index;
