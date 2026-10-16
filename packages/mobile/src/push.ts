import { Platform } from "react-native";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";
import { router } from "expo-router";
import { approveAction, registerPushToken, rejectAction } from "./api";

/**
 * Push notifications for the coworker: approvals (with Approve / Reject
 * buttons right on the notification), hot leads, calls it joined, and the
 * daily digest.
 */
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true, shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: true,
  }),
});

export async function registerForPush(): Promise<string | null> {
  if (!Device.isDevice) return null; // simulators can't receive pushes
  await Notifications.setNotificationCategoryAsync("approval", [
    { identifier: "approve", buttonTitle: "Approve", options: { opensAppToForeground: false } },
    { identifier: "reject", buttonTitle: "Reject", options: { opensAppToForeground: false, isDestructive: true } },
  ]);
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", { name: "Coworker", importance: Notifications.AndroidImportance.HIGH });
  }
  const current = await Notifications.getPermissionsAsync();
  let granted = current.granted;
  if (!granted) granted = (await Notifications.requestPermissionsAsync()).granted;
  if (!granted) return null;
  const projectId = (Constants.expoConfig as any)?.extra?.eas?.projectId ?? (Constants as any).easConfig?.projectId;
  const token = (await Notifications.getExpoPushTokenAsync(projectId ? { projectId } : undefined)).data;
  await registerPushToken(token);
  return token;
}

/** Act on a notification tap or button. Returns a cleanup function. */
export function listenForResponses(): () => void {
  const sub = Notifications.addNotificationResponseReceivedListener(async (response) => {
    const data = (response.notification.request.content.data || {}) as Record<string, any>;
    const action = response.actionIdentifier;
    if (data.type === "approval" && data.actionId) {
      if (action === "approve") {
        await approveAction(Number(data.actionId)).catch(() => router.push("/coworker"));
        return;
      }
      if (action === "reject") {
        await rejectAction(Number(data.actionId), "Rejected from a notification").catch(() => {});
        return;
      }
      router.push("/coworker");
    } else if (data.type === "call" && data.meetingId) {
      router.push(`/call/${data.meetingId}`);
    } else if (data.type === "autojoin" && data.chatId) {
      router.push({ pathname: "/chat", params: { session: String(data.chatId) } });
    } else if (["today", "autojoin", "autojoin_failed"].includes(String(data.type))) {
      router.push({ pathname: "/coworker", params: { tab: "today" } });
    } else if (data.url === "/coworker/settings") {
      router.push("/coworker");  // reconnect prompts: settings live on the web app
    }
  });
  return () => sub.remove();
}
