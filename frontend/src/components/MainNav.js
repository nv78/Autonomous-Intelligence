import { React, useEffect, useState } from "react";
import { logout, refreshCredits, useNumCredits } from "../redux/UserSlice";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  accountPath,
  selectWorkflowsPath,
  chatbotPath,
  apiKeyDashboardPath,
  downloadPrivateGPTPath
} from "../constants/RouteConstants";
import { Dropdown, Navbar, Avatar, DarkThemeToggle } from "flowbite-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCoins } from "@fortawesome/free-solid-svg-icons";
import { useLocation } from "react-router-dom";
import { useUser, viewUser } from "../redux/UserSlice";

import { useHistory } from 'react-router-dom';


function MainNav(props) {
  const location = useLocation();
  let dispatch = useDispatch();
  let navigate = useNavigate();
  let user = useUser();
  console.log("user", user);
  let numCredits = useNumCredits();


  useEffect(() => {
    dispatch(viewUser());
  }, []);

  useEffect(() => {
    if (user && "id" in user) {
      // Start polling when the component mounts
      const intervalId = setInterval(() => {
        // dispatch(refreshCredits());
      }, 5000); // Poll every 5 seconds

      // Clear the polling interval when the component unmounts
      return () => clearInterval(intervalId);
    }
  }, [user]);

  var imageUrl = null;
  if (user && "profile_pic_url" in user) {
    imageUrl = user["profile_pic_url"];
  }

  return (
    <Navbar className="navbar-fixed bg-black text-white border-b-2" fluid rounded>
      <Navbar.Brand href="https://privatechatbot.ai">
        <div className="h-10 w-10 bg-center bg-contain bg-[url('../public/logonew.png')] dark:bg-[url('../public/logonew.png')]"></div>
        <span className="self-center whitespace-nowrap text-xl font-semibold dark:text-white text-white pl-3">
          Panacea
        </span>
      </Navbar.Brand>
      <div className="flex md:order-2">
      <div className="mr-4 my-2 py-1 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black rounded-2xl cursor-pointer"
          onClick={() => navigate(downloadPrivateGPTPath)}
        >
          <span className="px-4 text-sm font-bold  text-black">
            <FontAwesomeIcon icon={faCoins} className="mr-2" />
            Download Private Version
          </span>
        </div>
        <Dropdown
          theme={{
            arrowIcon: "text-white ml-2 h-4 w-4",
          }}
          className="bg-gray-950 text-white"
          inline
          label={
            imageUrl == "" ? (
              <Avatar rounded></Avatar>
            ) : (
              <Avatar img={imageUrl} rounded></Avatar>
            )
          }
        >
          <Dropdown.Header>
            {user && user.name && (
              <span className="block text-sm text-white">{user.name}</span>
            )}
            <span className="block truncate text-sm font-medium text-white hover:bg-[#141414]">
              {numCredits} Credits Remaining
              <FontAwesomeIcon icon={faCoins} className="ml-2" />
            </span>
          </Dropdown.Header>
          <Dropdown.Item onClick={() => navigate(accountPath)} className="text-white hover:text-black">
            Account
          </Dropdown.Item>
          <Dropdown.Item onClick={() => navigate(apiKeyDashboardPath)} className="text-white hover:text-black">
            API
          </Dropdown.Item> 
          <Dropdown.Divider/>
          <Dropdown.Item
            onClick={() =>
              dispatch(logout()).then((resp) => {
                navigate("/");
                props.setIsLoggedInParent(false);
              })
            }
            className="text-white hover:text-black"
          >
            Sign out
          </Dropdown.Item>
        </Dropdown>
        <Navbar.Toggle />
      </div>
    </Navbar>
  );
}

export default MainNav;
