import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const Companies = () => {
  const [companies, setCompanies] = useState([]);

  //check log in status
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const accessToken = localStorage.getItem("accessToken");
  const sessionToken = localStorage.getItem("sessionToken");
  if (accessToken || sessionToken) {
    if (!isLoggedIn) {
      setIsLoggedIn(true);
    }
  } else {
    if (isLoggedIn) {
      setIsLoggedIn(false);
    }
  }
  var showRestrictedRouteRequiringUserSession = isLoggedIn;

  useEffect(() => {
    axios.get("http://localhost:5050/api/companies", { //port 5050 because of conflicts with 5000
      withCredentials: true
    })  // Flask runs on port 5000
      .then(res => setCompanies(res.data))
      .catch(err => console.error("Error fetching companies:", err));
  }, []);

  return (
    <section className="text-gray-100 body-font overflow-hidden min-h-screen bg-black px-4 py-10">
      <div className="flex flex-col text-center w-full mb-10">
        <h1 className="sm:text-5xl text-4xl font-extrabold title-font bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent w-fit mx-auto px-4 py-2">
          Companies
        </h1>
      </div>

      <div className="container mx-auto flex flex-col sm:flex-row sm:justify-center sm:items-start gap-12 px-4">
        <div className="sm:w-1/2 w-full flex flex-col items-center">
          <h2 className="text-2xl font-semibold mb-6 text-center">Our Company Chatbots</h2>

          <div className="w-full max-w-md h-60 overflow-y-auto border border-gray-600 rounded-md p-4 space-y-4">
          {companies.map((company) => (
              <Link
                key={company.id}
                to={company.path}
                className="block border border-gray-600 hover:border-yellow-400 p-3 rounded-md text-center hover:bg-gray-800 transition"
              >
                {company.name}
              </Link>
            ))}
          </div>
        </div>

        <div className="sm:w-1/2 w-full flex flex-col items-center text-center">
          <h2 className="text-2xl font-semibold mb-3">Make Your Own</h2>
          <p className="text-sm text-gray-400 max-w-xs mb-6">
            Create an intelligent chatbot for your company, no coding necessary.
          </p>
          <Link to="/create-chatbot" className="btn-black px-6 py-2 border border-white rounded hover:bg-white hover:text-black transition">
            Get Started
          </Link>
        </div>
      </div>
    </section>
  );
};

export default Companies;