import React from "react";
import { logout, useNumCredits } from "../redux/UserSlice";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCoins } from "@fortawesome/free-solid-svg-icons";

function SideNav(props) {
  const tabNames = ["Home"];
  let dispatch = useDispatch();
  let navigate = useNavigate();

  let numCredits = useNumCredits();

  function onLogout() {
    dispatch(logout()).then((resp) => {
      // Handle the response if needed
      navigate("/");
      props.setIsLoggedInParent(false);
    });
  }

  return (
    <div className="SideNavComponent">
      <ul style={{ listStyleType: "none", padding: 0 }}>
        {tabNames.map((tabName, index) => (
          <li
            key={index}
            style={{
              padding: "10px",
              cursor: "pointer",
              backgroundColor: index === props.tabNum ? "#ccc" : "transparent",
            }}
            onClick={() => {
              if (index == 0) {
                navigate("/");
              }
              // else if (index == 3) {
              //   navigate(contactPath);
              // }
            }}
          >
            {tabName}
          </li>
        ))}
      </ul>
      <button
        onClick={onLogout}
        type="button"
        class="login-with-google-btn LogoutButton"
        style={{ width: "auto" }}
      >
        LOGOUT
      </button>
      <div>
        {numCredits} Credits Remaining{" "}
        <FontAwesomeIcon icon={faCoins} color="white" />
      </div>
    </div>
  );
}

export default SideNav;
