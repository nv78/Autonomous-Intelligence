/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "node_modules/flowbite-react/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        yellow: {
          100: "#f8ffda",
          200: "#f2ffb5",
          300: "#ebfe91",
          400: "#e5fe6c",
          500: "#40C6FF",
          600: "#b2cb39",
          700: "#85982b",
          800: "#59661c",
          900: "#2c330e",
        },
        turquoise: {
          100: "#d9f9f6",
          200: "#b3f3ec",
          300: "#8cece3",
          400: "#66e6d9",
          500: "#40e0d0",
          600: "#33b3a6",
          700: "#26867d",
          800: "#1a5a53",
          900: "#0d2d2a",
        },
        teal: {
          100: "#d4f0fe",
          200: "#a9e0fd",
          300: "#7ed1fd",
          400: "#53c1fc",
          500: "#28b2fb",
          600: "#208ec9",
          700: "#186b97",
          800: "#104764",
          900: "#082432",
        },
        anoteblack: {
          100: "#d2d3d3",
          200: "#a5a7a7",
          300: "#787a7c",
          400: "#4b4e50",
          500: "#1e2224",
          600: "#181b1d",
          700: "#121416",
          800: "#0c0e0e",
          900: "#060707",
        },
      },
    },
  },
  plugins: [require("flowbite/plugin")],
  // corePlugins: {
  //   preflight: false,
  // },
};
