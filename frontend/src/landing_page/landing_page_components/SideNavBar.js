import React, { useEffect } from "react";

function EntryToClass(entry) {
  return entry.replace(/\s/g, "").replace(/\?.*$/, "");
}

export default function SideNavBar(props) {
  var innerList = [];
  props.entries.forEach((entry) => {
    innerList.push(
      <a className={EntryToClass(entry)} href={"#" + EntryToClass(entry)}>
        <li className="mb-3">{entry}</li>
      </a>
    );
  });
  var list = <ul>{innerList}</ul>;

  useEffect(() => {
    // Add the event listener to the window object
    window.addEventListener("scroll", () => {
      // Get the current scroll position of the page
      const scrollPosition = window.pageYOffset;
      // Get the midpoint of the window
      const windowTop = 0;

      // Find the section with the midpoint closest to the midpoint of the window
      let closestSection = null;
      let closestDistance = Infinity;
      props.entries.forEach((entry) => {
        // Get the element that corresponds to the section
        const section = document.querySelector(`#${EntryToClass(entry)}`);
        if (!section) return;

        // Calculate the distance between the midpoint of the section and the midpoint of the window
        const sectionMidpoint = section.offsetTop + section.offsetHeight / 2;
        const distance = Math.abs(
          sectionMidpoint - (windowTop + scrollPosition)
        );

        // Check if this distance is closer than the previous closest distance
        if (distance < closestDistance) {
          closestSection = entry;
          closestDistance = distance;
        }
      });

      // Update the active section in the navbar
      props.entries.forEach((entry) => {
        // Get the link element
        const link = document.querySelector(`.${EntryToClass(entry)}`);
        if (!link) return;

        if (entry === closestSection) {
          link.classList.add("font-bold");
          link.classList.add("text-white");
        } else {
          link.classList.remove("font-bold");
          link.classList.remove("text-white");
        }
      });
    });

    // Remove the event listener when the component unmounts to avoid memory leaks
    return () => {
      window.removeEventListener("scroll", () => {});
    };
  }, []); // The empty array ensures that the effect only runs once when the component mounts

  return (
    <div className={"hidden md:block fixed right-5 top-44 w-3/12"}>
      <h4 className="font-semibold text-white text-xl mb-3">{props.title}</h4>
      <div className="border-l-2 border-[#EDDC8F] pl-5 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent text-lg">
        {list}
      </div>
    </div>
  );
}
