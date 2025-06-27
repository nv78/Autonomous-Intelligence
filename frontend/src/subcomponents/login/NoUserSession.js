import { useDispatch } from "react-redux";
import { login } from "../../redux/UserSlice";
import React, { useState, useEffect } from "react";
import "../../styles/Login.css";
import LoginComponent from "./LoginComponent";
import SignUpComponent from "./SignUpComponent";
import ForgotPasswordComponent from "./ForgotPasswordComponent";
import PasswordReset from "./PasswordReset";
import { useLocation } from "react-router-dom";
import googleIcon from '../../assets/google_button_blue_enh.png';
import { Modal, Button } from 'flowbite-react';

function NoUserSession(props) {
  let dispatch = useDispatch();
  const onLogin = () => {
    dispatch(
      login({
        product_hash: props.productHash,
        free_trial_code: props.freeTrialCode,
      })
    );
  };

  // 1: login
  // 2: sign up
  // 3: forget password
  // 4: password reset
  const [pageState, setPageState] = useState(1);
  const [statusMessage, setStatusMessage] = useState("");
  const [showVideoModal, setShowVideoModal] = useState(false);

  function setPageStateWithReset(newState) {
    setPageState(newState);
    setStatusMessage("");
  }

  const location = useLocation();
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState("");
  const [forgotPasswordCode, setForgotPasswordCode] = useState("");

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const emailParam = queryParams.get("email");
    const codeParam = queryParams.get("passwordResetCode");

    if (emailParam && codeParam) {
      setForgotPasswordEmail(emailParam);
      setForgotPasswordCode(codeParam);
      setPageState(4);
    }
  }, []);

  return (
    // <div className=" bg-[#141414] min-h-screen">
    <div className="flex flex-col min-h-screen bg-[#141414]">
    <div className="flex-grow">
      <h1 className="UpreachTitle companyName text-4xl font-semibold flex justify-center pt-10">
        <img src="logonew.png" className="w-10 h-10" alt="logo" />
        <span className=" pl-3">Panacea</span>
      </h1>
      <h2 className="text-2xl text-center text-[#F1CA57] font-semibold my-2">
        Build Multi Agent AI Systems
      </h2>
      <Button className="mx-auto mb-4 btn-yellow text-black" variant="primary" onClick={() => setShowVideoModal(true)}>
          See How It Works
      </Button>
      <Modal size={"7xl"} show={showVideoModal} onClose={() => setShowVideoModal(false)} className="bg-gray-950">
          <Modal.Header className="bg-[#141414] text-white p-4">
            See How It Works
          </Modal.Header>
          <Modal.Body className="p-4 flex items-center justify-center bg-[#141414]
">
              <div style={{position: "relative", width: "100%", paddingBottom: "56.25%"}}>
                  <a style={{position: "absolute", top: "70px", right: "1rem", opacity: 0.8}} href="https://clipchamp.com/watch/UoPz2Tjbykg?utm_source=embed&utm_medium=embed&utm_campaign=watch">
                      <img loading="lazy" style={{height: "30px"}} src="https://clipchamp.com/e.svg" alt="Made with Clipchamp" />
                  </a>
                  <iframe
                      allow="autoplay;"
                      allowFullScreen
                      style={{position: "absolute", top: "0", left: "0", width: "100%", height: "100%", border: "none"}}
                      src="https://www.youtube.com/embed/SW6itfZ2nmg"
                  ></iframe>
              </div>
          </Modal.Body>
      </Modal>


      <div class="w-full md:w-1/3 mx-auto text-white py-8">
        <div class="bg-gray-950 rounded-xl border-gray-300 border-2 text-center pt-3">
          {pageState == 1 && (
            <LoginComponent
              setPageState={setPageStateWithReset}
              statusMessage={statusMessage}
              setStatusMessage={setStatusMessage}
            />
          )}
          {pageState == 2 && (
            <SignUpComponent
              setPageState={setPageStateWithReset}
              statusMessage={statusMessage}
              setStatusMessage={setStatusMessage}
            />
          )}
          {pageState == 3 && (
            <ForgotPasswordComponent
              setPageState={setPageStateWithReset}
              statusMessage={statusMessage}
              setStatusMessage={setStatusMessage}
            />
          )}
          {pageState == 4 && (
            <PasswordReset
              forgotPasswordEmail={forgotPasswordEmail}
              forgotPasswordCode={forgotPasswordCode}
              setPageState={setPageStateWithReset}
              statusMessage={statusMessage}
              setStatusMessage={setStatusMessage}
            />
          )}
          {pageState != 3 && pageState != 4 && (
            <p className="text-center my-4">
              ---------------- Or ----------------
            </p>
          )}
          {pageState != 3 && pageState != 4 && (
            <button
              onClick={onLogin}
              type="button"
              className="login-with-google-btn-new"
              style={{ backgroundImage: `url(${googleIcon})`, textColor: "transparent"}}
            />
          )}
        </div>
      </div>
    </div>
    </div>
  );
}

export default NoUserSession;
