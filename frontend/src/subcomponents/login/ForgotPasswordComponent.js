import React from "react";
import { useDispatch } from "react-redux";
import { useState } from "react";
import { forgotPassword } from "../../redux/UserSlice";
import { TextInput } from "flowbite-react";

function ForgotPasswordComponent(props) {
  let dispatch = useDispatch();

  const [email, setEmail] = useState("");

  function onHandlePressForgotPassword() {
    props.setStatusMessage("");
    if (!email) {
      props.setStatusMessage("Must enter an email address");
    } else {
      dispatch(forgotPassword({ email: email }));
      props.setStatusMessage("Password reset link sent to email address");
    }
  }

  return (
    <div className="flex flex-col items-center mb-4">
      <h1 className="my-4 font-bold text-3xl">Reset Password</h1>
      <p className={"resetPasswordText ml-20 mr-20"}>
        Enter email address and we will send instructions to reset your password
      </p>
      <TextInput
        id="dsearch"
        name="dsearch"
        placeholder="Enter Email"
        required
        type="email"
        onChange={(e) => {
          setEmail(e.target.value);
        }}
        className="my-2 w-1/2 mx-auto"
      />
      <button
        onClick={() => {
          onHandlePressForgotPassword();
        }}
        className="ButtonType6"
        style={{ marginTop: "20px" }}
      >
        Continue
      </button>
      <p
        className={"UncursorableButton mt-2"}
        onClick={() => {
          props.setPageState(1);
        }}
        style={{ color: "#F1CA57" }}
      >
        Back to Panacea
      </p>
      {props.statusMessage && (
        <p style={{ color: "#F1CA57" }}>{props.statusMessage}</p>
      )}
    </div>
  );
}

export default ForgotPasswordComponent;
