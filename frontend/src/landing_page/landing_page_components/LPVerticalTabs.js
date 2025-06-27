import React, { useState } from "react";
import "../landing_page_styles/LandingPageVerticalTabs.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronLeft,
  faChevronRight,
} from "@fortawesome/free-solid-svg-icons";
import Modal from "react-modal";
Modal.setAppElement("#root");

function LPVerticalTabs({ heading, object }) {
  const [modalIsOpen, setIsOpen] = useState(false);
  const openModal = () => {
    setIsOpen(true);
  };

  const closeModal = () => {
    setIsOpen(false);
  };

  const [currentIndex, setCurrentIndex] = useState(0);

  const handleNext = () => {
    if (currentIndex < object.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setCurrentIndex(0);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    } else {
      setCurrentIndex(object.length - 1);
    }
  };

  const [selectedCapability, setSelectedCapability] = useState(object[0].name);

  const currentImage = object.find(
    (object) => object.name === selectedCapability
  ).image;

  return (
    <div className="mx-4 h-full">
      <div className="text-3xl sm:text-4xl lg:text-5xl my-10 text-center font-medium lg:font-bold">
        {heading}
      </div>
      <div className="md:hidden">
        <div className="flex flex-row justify-between items-center">
          <FontAwesomeIcon
            icon={faChevronLeft}
            size="2xl"
            className="text-[#40C6FF]"
            onClick={handlePrevious}
          />
          <div className="flex flex-col justify-center items-center">
            <div className="w-11/12 border-sky-300 border-2 rounded-xl">
              <img
                className="object-cover object-center rounded-lg"
                src={object[currentIndex].image}
                alt={object[currentIndex].name}
                onClick={openModal}
                loading="lazy"
              />
              <Modal
                isOpen={modalIsOpen}
                onRequestClose={closeModal}
                contentLabel="Image Modal"
                className={"w-11/12 mt-32 mx-auto"}
                style={{
                  overlay: {
                    backgroundColor: "rgba(0, 0, 0, 0.5)",
                  },
                  content: {
                    // display: "flex",
                    // justifyContent: "center",
                    // alignItems: "center",
                    backgroundColor: "transparent",
                    border: "none",
                  },
                }}
              >
                <img
                  className="object-cover object-center rounded-lg"
                  src={object[currentIndex].image}
                  alt={object[currentIndex].name}
                  onClick={closeModal}
                  loading="lazy"
                />
              </Modal>
            </div>
          </div>
          <FontAwesomeIcon
            icon={faChevronRight}
            size="2xl"
            className="text-[#40C6FF]"
            onClick={handleNext}
          />
        </div>
        <div className="text-center text-3xl text-[#40C6FF] my-10">
          {object[currentIndex].name}
        </div>
        <div className="md:hidden flex justify-center items-center mt-2">
          {object.map((item, index) => (
            <div
              key={index}
              className={`h-1 w-1 mr-2 rounded-full ${
                currentIndex === index ? "bg-turquoise-500" : "bg-gray-300"
              }`}
            />
          ))}
        </div>
      </div>
      <div className="hidden md:block w-11/12 lg:w-4/5 mx-auto bg-[#141414]
 rounded-2xl">
        <div className="flex justify-evenly">
          <div className="flex flex-col justify-evenly text-xl hover:cursor-pointer">
            {object.map((object, index) => (
              <div
                key={index}
                className={`${
                  selectedCapability === object.name
                    ? " bg-[#141414]
 text-white font-semibold py-3 px-3 rounded-xl"
                    : " text-[#40C6FF] hover:text-sky-200"
                }`}
                onClick={() => setSelectedCapability(object.name)}
              >
                {object.name}
              </div>
            ))}
          </div>
          <div className="w-4/6">
            <img
              className="w-full"
              src={currentImage}
              alt={selectedCapability}
              loading="lazy"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default LPVerticalTabs;
