import { IsDashboardSubdomain } from "./util/DomainParsing";
import Dashboard from "./Dashboard";
import LandingPage from "./landing_page/LandingPage";
import { BrowserRouter as Router} from "react-router-dom";

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
        <LandingPage />
      </Router>
    );
  }
}

export default App;

