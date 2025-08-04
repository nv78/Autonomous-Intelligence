import { useNavigate } from "react-router-dom";
import "../landing_page_styles/LandingPageNavbar.css";
import "../landing_page_styles/LandingPageButtons.css";
import React, { useState } from "react";
import { HashLink as Link } from "react-router-hash-link";
import NavLinks from "./NavLinks";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBars,
  faXmark,
  faArrowRight,
  faA,
} from "@fortawesome/free-solid-svg-icons";

function Navbar(props) {
  const [hovered, setHovered] = useState(false);

  const navigate = useNavigate();

  const urlObject = new URL(window.location.origin);

  function handleTutorialButtonClick() {
      // window.open("https://www.youtube.com/watch?v=SW6itfZ2nmg", "_blank");
      navigate("/tutorials");
  }
  var hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `dashboard.${hostname}`;

  var startPath = urlObject.toString();
  return (
    <nav className="sticky top-0 h-[4.5rem] md:h-20 md:h-18 w-full bg-[#141414]
 text-white z-30">
      <div className="flex items-center font-medium justify-around">
        <div className="flex items-start">
{/*
          <div className="p-5 lg:w-auto w-full flex z-40">
            <div className="flex flex-row left-2 absolute lg:static">
              <div
                className={`rocket-container ${hovered ? "rocket-fly" : ""}`}
                onMouseEnter={() => setHovered(true)}
                onMouseLeave={() => setHovered(false)}
              >
                <img
                  src="/logo.png"
                  alt="logo"
                  className="lg:cursor-pointer h-9"
                  onAnimationEnd={() => setHovered(false)}
                />
                <Link
                  to="/#top"
                  className="font-bold text-3xl lg:cursor-pointer font-['Helvetica_Neue']"
                >
                  Private Chatbot
                </Link>
              </div>
            </div> */}
            <div className="p-5 lg:w-auto w-full z-40">
  <div className="flex flex-row items-center left-2 absolute lg:static">
    <div
      className={`rocket-container ${hovered ? "rocket-fly" : ""} flex items-center`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <img
        src="/logonew.png"
        alt="logo"
        className="lg:cursor-pointer h-9"
        onAnimationEnd={() => setHovered(false)}
      />
      <Link
        to="/#top"
        className="font-bold text-3xl lg:cursor-pointer font-['Helvetica_Neue'] ml-2" // Added ml-2 for some spacing between the logo and text
      >
        Panacea
      </Link>
    </div>
  </div>

            <div
              className="text-3xl lg:hidden right-3 absolute"
              onClick={() => props.setOpen(!props.open)}
            >
              <FontAwesomeIcon icon={props.open ? faXmark : faBars} />
            </div>
          </div>
        </div>
        <ul className="lg:flex hidden items-center gap-8 ">
          <NavLinks />
        </ul>
        <div className="lg:block hidden items-start">
          <button onClick={handleTutorialButtonClick} className="btn-black">
            View Tutorials
          </button>
          <button
            onClick={() => {
              window.location.assign(startPath);
            }}
            class="btn-yellow ml-4"
          >
            Get Started
          </button>
        </div>

        <ul
          className={`lg:hidden bg-[#141414]
 fixed w-full h-full top-0 py-24 pl-4 z-20 duration-500 ${
            props.open ? "left-0" : "left-[-100%]"
          }`}
        >
          <li>
            <NavLinks isOpen={props.open} setIsOpen={props.setOpen} />
            <div className="py-5">
              {/* <button
                onClick={handleTutorialButtonClick}
                className="btn-black mb-5 w-max"
              >
                View Tutorials
              </button> */}
              <button
                onClick={() => {
                  window.location.assign(startPath);
                }}
                class="btn-yellow w-max ml-4"
              >
                Get Started
              </button>
            </div>
          </li>
        </ul>
      </div>
    </nav>
  );
}

export default Navbar;
