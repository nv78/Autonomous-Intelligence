import { React, useEffect, useState } from "react";
import { logout, refreshCredits, useNumCredits } from "../redux/UserSlice";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  accountPath,
  selectWorkflowsPath,
  chatbotPath,
  apiKeyDashboardPath,
  downloadPrivateGPTPath,
  gtmPath,
  landing,
  chatbots,
} from "../constants/RouteConstants";
import { Dropdown, Navbar, Avatar, DarkThemeToggle } from "flowbite-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCoins } from "@fortawesome/free-solid-svg-icons";
import { useLocation } from "react-router-dom";
import { useUser, viewUser } from "../redux/UserSlice";

import { useHistory } from "react-router-dom";
import { Link } from "react-router-dom";

// function MainNav(props) {
//   const location = useLocation();
//   let dispatch = useDispatch();
//   let navigate = useNavigate();
//   let user = useUser();
//   console.log("user", user);
//   let numCredits = useNumCredits();

//   useEffect(() => {
//     dispatch(viewUser());
//   }, []);

//   // useEffect(() => {
//   //   if (user && "id" in user) {
//   //     // Start polling when the component mounts
//   //     const intervalId = setInterval(() => {
//   //       // dispatch(refreshCredits());
//   //     }, 5000); // Poll every 5 seconds

//   //     // Clear the polling interval when the component unmounts
//   //     return () => clearInterval(intervalId);
//   //   }
//   // }, [user]);

//   var imageUrl = null;
//   if (user && "profile_pic_url" in user) {
//     imageUrl = user["profile_pic_url"];
//   }

//   return (
//     // <Navbar className="fixed w-full z-50 bg-anoteblack-800" fluid>
//     //   {/* <Navbar.Brand href="https://privatechatbot.ai"> */}
//     //   <Navbar.Brand onClick={() => navigate(landing)}>
//     //     <div className="h-8 w-8 bg-center bg-contain bg-[url('../public/logonew.png')] dark:bg-[url('../public/logonew.png')]"></div>
//     //     <span className="self-center md:block hidden whitespace-nowrap text-lg font-semibold text-white pl-2">
//     //       Panacea
//     //     </span>
//     //   </Navbar.Brand>
//     //   <div className="flex items-center md:order-2">
//     //     <div
//     //       className="mr-3 my-1 py-1 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black rounded-2xl cursor-pointer"
//     //       onClick={() => navigate(downloadPrivateGPTPath)}
//     //     >
//     //       <span className="px-3 text-xs font-bold text-black">
//     //         <FontAwesomeIcon icon={faCoins} className="mr-1" />
//     //         Download Private Version
//     //       </span>
//     //     </div>
//     //     <div
//     //       className="text-white text-xs font-medium cursor-pointer mr-3"
//     //       onClick={() => navigate(chatbots)}
//     //     >
//     //       Chatbots
//     //     </div>
//     //     <Dropdown
//     //       theme={{
//     //         arrowIcon: "text-white ml-2 h-4 w-4",
//     //       }}
//     //       className="bg-gray-950 text-white"
//     //       inline
//     //       label={
//     //         imageUrl == "" ? (
//     //           <Avatar rounded />
//     //         ) : (
//     //           <Avatar img={imageUrl} rounded />
//     //         )
//     //       }
//     //     >
//     //       <Dropdown.Header>
//     //         {user && user.name && (
//     //           <span className="block text-sm text-white">{user.name}</span>
//     //         )}
//     //         <span className="block truncate text-sm font-medium text-white hover:bg-[#141414]">
//     //           {numCredits} Credits Remaining
//     //           <FontAwesomeIcon icon={faCoins} className="ml-2" />
//     //         </span>
//     //       </Dropdown.Header>
//     //       <Dropdown.Item
//     //         onClick={() => navigate(accountPath)}
//     //         className="text-white hover:text-black"
//     //       >
//     //         Account
//     //       </Dropdown.Item>
//     //       <Dropdown.Item
//     //         onClick={() => navigate(apiKeyDashboardPath)}
//     //         className="text-white hover:text-black"
//     //       >
//     //         API
//     //       </Dropdown.Item>
//     //       <Dropdown.Divider />
//     //       <Dropdown.Item
//     //         onClick={() =>
//     //           dispatch(logout()).then(() => {
//     //             navigate("/");
//     //             props.setIsLoggedInParent(false);
//     //           })
//     //         }
//     //         className="text-white hover:text-black"
//     //       >
//     //         Sign out
//     //       </Dropdown.Item>
//     //     </Dropdown>
//     //   </div>
//     // </Navbar>
//     <div>hello</div>
//   );
// }

function MainNav(props) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const user = useUser();
  const [showUserDropdown, setShowUserDropdown] = useState(false);

  const handleLogout = () => {
    dispatch(logout()).then((resp) => {
      navigate("/");
      if (props.setIsLoggedInParent) {
        props.setIsLoggedInParent(false);
      }
      // Reload the page to reset state
      window.location.reload();
    });
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showUserDropdown && !event.target.closest(".user-dropdown")) {
        setShowUserDropdown(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showUserDropdown]);

  const urlObject = new URL(window.location.origin);
  var hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `dashboard.${hostname}`;

  let imageUrl = null;
  if (user && "profile_pic_url" in user) {
      imageUrl = user["profile_pic_url"];
  }

  return (
    <nav
      className={`fixed  ${
        props.menu && !props.isGuestMode ? "ml-80" : "ml-0"
      }  top-0 left-0 right-0 bg-anoteblack-900 z-50`}
    >
      <div
        className={`flex items-center justify-between px-4 py-4 max-w-7xl mx-auto`}
      >
        {/* Left side - Sidebar toggle and Brand name */}
        <div className="flex items-center space-x-3">
          {/* Sidebar toggle button - only show when logged in */}
          {!props.isGuestMode && (
            <button
              onClick={props.handleMenu}
              className={`p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors ${
                props.menu ? "hidden" : "block"
              }`}
              title="Toggle chat history"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
          )}

          <div className="md:flex hidden items-center space-x-2">
            <h1 className="text-white font-semibold text-lg">Panacea</h1>
            {props.isGuestMode && (
              <span className="text-xs text-gray-300 bg-gray-700 px-2 py-1 rounded-full ml-2">
                Guest
              </span>
            )}
          </div>
        </div>

        {/* Right side - Auth buttons */}
        <div className="flex items-center space-x-3">
          {props.isGuestMode ? (
            <>
              <button
                onClick={() => props.onRequestLogin && props.onRequestLogin()}
                className="text-gray-300 hover:text-white px-3 py-1.5 text-sm font-medium transition-colors"
              >
                Log in
              </button>
              <button
                onClick={() => props.onRequestLogin && props.onRequestLogin()}
                className="bg-white hover:bg-gray-100 text-black px-4 py-1.5 rounded-lg text-sm font-medium transition-colors"
              >
                Sign up for free
              </button>
            </>
          ) : (
            <div className="relative user-dropdown">
              <button
                onClick={() => setShowUserDropdown(!showUserDropdown)}
                className="flex items-center space-x-2 p-1 rounded-lg hover:bg-gray-700 transition-colors"
              >
                <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center">
                  {imageUrl === null ? (
                    <span className="text-sm font-medium text-gray-300">U</span>
                  ) : (
                    <img className="rounded-full" src={imageUrl} alt={user.profile_pic_url} />
                  )}
                </div>
                <svg
                  className={`w-4 h-4 text-gray-400 transform transition-transform ${
                    showUserDropdown ? "rotate-180" : ""
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {/* Dropdown menu */}
              {showUserDropdown && (
                <div className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50">
                  <div className="py-1">
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                    >
                      Log out
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

export default MainNav;
