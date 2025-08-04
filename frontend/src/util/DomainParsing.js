import { faqsPath } from './../constants/RouteConstants';

export function IsDashboardSubdomain() {
    // Get the full hostname from the location object
    const hostname = window.location.hostname;
    const hostnameParts = hostname.split('.');
    // If the hostname has more than two parts, the first part is the subdomain
    if (hostnameParts.length > 1) {
      const subdomain = hostnameParts[0];
      if (subdomain === "dashboard") {
        return true;
      } else {
        return false;
      }
    } else {
      // If there is no subdomain, return false
      return false;
    }
}

export function GetDashboardUrl() {
  return `https://dashboard.anote.ai`;
}

export function GetUpreachUrl() {
  return `https://upreach.anote.ai`;
}

export function GetPrivateGPTDashboardUrl() {
  return `https://privatechatbot.ai`;
}
