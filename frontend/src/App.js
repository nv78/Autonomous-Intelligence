import { IsDashboardSubdomain } from "./util/DomainParsing";
import Dashboard from "./Dashboard";
import LandingPage from "./landing_page/LandingPage";
import CheckLogin from "./components/CheckLogin";
import { BrowserRouter as Router, Routes, Route} from "react-router-dom";

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

