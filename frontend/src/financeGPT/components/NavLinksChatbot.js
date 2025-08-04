import React from "react";

const NavLinksChatbot = ({ open, setOpen }) => {

  const links = [
    {
      name: "Home",
      submenu: false,
      new_tab: false,
      link: "/chatbot",
    },
    {
      name: "10-K Edgar",
      submenu: false,
      new_tab: false,
      link: "/edgar",
    },
    {
      name: "PDF Uploader",
      submenu: false,
      new_tab: false,
      link: "/pdfchatbot",
    },
    {
      name: "All Doctypes",
      submenu: false,
      new_tab: false,
      link: "/alldocs",
    },
    {
      name: "MySQL Connector",
      submenu: false,
      new_tab: false,
      link: "/sqlconnector",
    },
  ];
  return (
    <ul className="space-y-1 bg-[#141414]
">
    {links.map((link) => (
      <li key={link.name} className="w-full">
        <a
          className={`flex items-center px-3 py-2 text-lg font-medium text-gray-100 rounded transition-colors ${
            // Apply active styles if this is the current path
            window.location.pathname === link.link ? 'text-white bg-gradient-to-r from-[#2E5C82] to-[#40C6FF]' : 'hover:text-white hover:bg-gray-700'
          }`}
          href={link.link}
          target={link.new_tab ? "_blank" : "_self"}
        >
          {link.name}
        </a>
      </li>
    ))}
  </ul>
  );
};

export default NavLinksChatbot;
