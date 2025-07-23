// import { IsDashboardSubdomain } from "./util/DomainParsing";
// import Dashboard from "./Dashboard";
// import LandingPage from "./landing_page/LandingPage";
// import CheckLogin from "./components/CheckLogin";
// //new
// import SharedChatViewer from "./components/SharedChatViewer";
// import { BrowserRouter as Router, Routes, Route} from "react-router-dom";

// function App() {
//   var isDashboardSubdomain = IsDashboardSubdomain();
//   if (isDashboardSubdomain) {
//     return (
//       <Router>
//         <Routes>
//           <Route path="/" element={<Dashboard />} />

//           {/* Shared chat route */}
//           <Route path="/playbook/:shareUuid" element={<SharedChatViewer />} />

//           <Route path="*" element={<Dashboard />} />
//         </Routes>
//       </Router>
//     );
//   } else {
//     return (
//       <Router>
//         <Routes>
//           <Route path="/" element={<LandingPage />} />
//           <Route path="/chat" element={<CheckLogin setIsLoggedInParent={() => {}} />} />
//           <Route path="/playbook/:shareUuid" element={<SharedChatViewer />} />
//         </Routes>
//       </Router>
//     );
//   }
// }

// export default App;

import { IsDashboardSubdomain } from "./util/DomainParsing";
import Dashboard from "./Dashboard";
import LandingPage from "./landing_page/LandingPage";
import { BrowserRouter as Router, Routes, Route} from "react-router-dom";
import CheckLogin from "./components/CheckLogin";

function App() {
  var isDashboardSubdomain = IsDashboardSubdomain();
  if (isDashboardSubdomain) {
    return (
      <Router>
        <Dashboard />
      </Router>
    );
  } else {
    return (
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/chat" element={<CheckLogin setIsLoggedInParent={() => {}} />} />
        </Routes>
      </Router>
    );
  }
}

export default App;
