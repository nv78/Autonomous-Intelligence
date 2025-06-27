import React, { useState } from "react";
import { Link, BrowserRouter as Router } from "react-router-dom";
import CheckLogin from "./components/CheckLogin";
import MainNav from "./components/MainNav";
import { Helmet } from "react-helmet";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  accountPath,
  pricingRedirectPath,
  chatbotPath,
  apiKeyDashboardPath,
  downloadPrivateGPTPath,
  connectorOptions // Import connector options from RouteConstants
} from "./constants/RouteConstants";
import PaymentsComponent from "./subcomponents/payments/PaymentsComponent";
import PaymentsProduct from "./subcomponents/payments/PaymentsProduct";
import { Flowbite } from "flowbite-react";
import { refreshCredits, useUser, viewUser } from "./redux/UserSlice";
import { useDispatch } from "react-redux";
import { useEffect } from "react";
import Workflows from "./components/Workflows"
import Home from "./financeGPT/components/Home";
import { APISKeyDashboard } from "./subcomponents/api/APISKeyDashboard";
import DownloadPrivateGPT from "./components/DownloadPrivateGPT.js";

function Dashboard() {
  const [darkTheme, setDarkTheme] = useState(true);
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

  let dispatch = useDispatch();

  useEffect(() => {
    if (isLoggedIn) {
      dispatch(viewUser());
      // dispatch(refreshCredits());
    }
  }, [isLoggedIn]);

  let user = useUser();

  var showRestrictedRouteRequiringPayments = false;
  if (user && user["paid_user"] != 0) {
    showRestrictedRouteRequiringPayments = true;
  }

  var isFreeTrial = false;
  if (user && user["is_free_trial"] == true) {
    isFreeTrial = true;
  }
  var numDaysLeft = "";
  if (user && user["end_date"]) {
    var currentDate = new Date();
    var endDate = new Date(user["end_date"]);
    var timeDifference = endDate - currentDate;
    var daysDifference = Math.ceil(timeDifference / (1000 * 60 * 60 * 24));
    numDaysLeft = daysDifference.toString();
  }

  // TODO: If you want to enabled restricted routes by default for
  // specific users.
  // if (user && user["email"]) {
  //   var userEmail = user["email"];
  //   if (
  //     userEmail == "t.clifford@wustl.edu" ||
  //     userEmail == "vidranatan@gmail.com" ||
  //     userEmail == "raghuwanshi.rajat10@gmail.com"
  //   ) {
  //     showRestrictedRouteRequiringPayments = true;
  //   }
  // }

  // Dynamically generate routes for connector options
  const connectorRoutes = connectorOptions.map((option) => (
    <Route key={option.value} path={option.path} element={<Home />} />
  ));

  var routes = [
    <Route
      index
      element={
        <CheckLogin
          darkTheme={darkTheme}
          setIsLoggedInParent={setIsLoggedIn}
          showRestrictedRouteRequiringPayments={
            showRestrictedRouteRequiringPayments
          }
        />
      }
    />,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={accountPath} element={<PaymentsComponent />} />
    ) : null,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={pricingRedirectPath} element={<PaymentsProduct />} />
    ) : null,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={chatbotPath} element={<Home />} />
    ) : null,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={downloadPrivateGPTPath} element={<DownloadPrivateGPT />} />
    ) : null,
    // showRestrictedRouteRequiringUserSession ? (
    //   <Route path={selectWorkflowsPath} element={<SelectWorkflow />} />
    // ) : null,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={apiKeyDashboardPath} element={<APISKeyDashboard />} />
    ) : null,
  ];

  var daysStr = "";
  if (numDaysLeft == "0") {
    daysStr = "less than a day";
  } else if (numDaysLeft == "1") {
    daysStr = "1 day";
  } else {
    daysStr = numDaysLeft.toString() + " days";
  }

  return (
    <Flowbite
      // theme={{
      //   dark: darkTheme,
      // }}
    >
      <div className="DashboardView flex flex-col min-h-screen">
        <div id="wrapperDiv" className="flex-grow">
          {/* {isLoggedIn && isFreeTrial && <div className="mt-2 mb-2 ml-6" style={{ color: "white" }}>
            Your free trial ends in {daysStr}
            <Link to={accountPath} className="ml-3 text-blue-500">Upgrade</Link>
          </div>} */}
          {isLoggedIn && (
            <MainNav
              // darkTheme={darkTheme}
              // setDarkTheme={setDarkTheme}
              setIsLoggedInParent={setIsLoggedIn}
            />
          )}
          <Helmet>
            <title>Panacea</title>
          </Helmet>
          <Routes>
            {routes}
            {connectorRoutes}
            <Route path="*" element={<Navigate replace to="/" />} />
          </Routes>
        </div>
      </div>
    </Flowbite>
  );
}
export default Dashboard;