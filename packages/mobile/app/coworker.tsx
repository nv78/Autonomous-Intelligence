import React, { useCallback, useEffect, useState } from "react";
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView, TextInput, RefreshControl, Alert,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useAppTheme } from "./_layout";
import {
  CoworkerAction, DayEntry, Meeting, approveAction, getCoworkerStatus, getDay, getDigest, getMeetings, getPendingActions,
  rejectAction, setCoworkerPaused, tickCoworker,
} from "../src/api";

type Tab = "approvals" | "today" | "calls";
const DAY_ICON: Record<string, string> = { meeting: "📞", brief: "📋", escalation: "🙋", security: "🛡️", digest: "🗞️" };

const POLL_MS = 15000;
const ICON: Record<string, string> = {
  "email.send": "✉️", "slack.post": "💬", "calendar.create": "📅", "crm.update": "🗂️", "responsibility.create": "📌",
};

/** Approve your coworker's actions from your phone, and stop everything with one tap. */
export default function CoworkerScreen() {
  const { theme } = useAppTheme();
  const [actions, setActions] = useState<CoworkerAction[]>([]);
  const [status, setStatus] = useState<{ exists: boolean; status?: string; pending?: number }>({ exists: true });
  const [headline, setHeadline] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const params = useLocalSearchParams<{ tab?: string }>();
  const [tab, setTab] = useState<Tab>((params.tab as Tab) || "approvals");
  const [day, setDay] = useState<{ headline: string; entries: DayEntry[] } | null>(null);
  const [calls, setCalls] = useState<Meeting[]>([]);

  const load = useCallback(async () => {
    try {
      await tickCoworker().catch(() => {});
      const [s, a, d] = await Promise.all([getCoworkerStatus(), getPendingActions(), getDigest().catch(() => null)]);
      setStatus(s);
      setActions(a);
      if (d) setHeadline(d.headline);
      if (tab === "today") setDay(await getDay());
      if (tab === "calls") setCalls(await getMeetings());
    } catch {}
  }, [tab]);

  useEffect(() => {
    load();
    const h = setInterval(load, POLL_MS);
    return () => clearInterval(h);
  }, [load]);

  const paused = status.status === "paused";

  const approve = async (a: CoworkerAction) => {
    const started = Date.now();
    try {
      await approveAction(a.id, editing === a.id && draft ? { body: draft, text: draft } : undefined);
      setEditing(null);
      setActions((list) => list.filter((x) => x.id !== a.id));
      if (Date.now() - started > 10000) Alert.alert("Approved", "That took longer than usual.");
    } catch (e: any) {
      Alert.alert("Couldn't approve", e?.response?.data?.error || "Try again.");
    }
  };

  const reject = (a: CoworkerAction) => {
    Alert.prompt?.("Reject", "What should it do differently? (optional)", async (feedback) => {
      await rejectAction(a.id, feedback || "");
      setActions((list) => list.filter((x) => x.id !== a.id));
    }) ?? rejectAction(a.id).then(() => setActions((list) => list.filter((x) => x.id !== a.id)));
  };

  const killSwitch = async () => {
    await setCoworkerPaused(!paused);
    load();
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerBtn}>
          <Text style={{ fontSize: 16, color: theme.text }}>{"‹ Chat"}</Text>
        </TouchableOpacity>
        <Text style={[styles.title, { color: theme.text }]}>Coworker</Text>
        <TouchableOpacity
          onPress={killSwitch}
          style={[styles.kill, { backgroundColor: paused ? "#F59E0B" : theme.surfaceAlt }]}
          accessibilityLabel={paused ? "Resume coworker" : "Pause coworker"}
        >
          <Text style={{ color: paused ? "#111" : theme.text, fontWeight: "600", fontSize: 13 }}>
            {paused ? "▶ Resume" : "⏸ Pause"}
          </Text>
        </TouchableOpacity>
      </View>

      <View style={[styles.tabs, { borderBottomColor: theme.border }]}>
        {(["approvals", "today", "calls"] as Tab[]).map((t) => (
          <TouchableOpacity key={t} onPress={() => setTab(t)}
            style={[styles.tab, tab === t && { borderBottomColor: theme.text }]}>
            <Text style={{ color: tab === t ? theme.text : theme.textMuted, fontWeight: tab === t ? "600" : "400" }}>
              {t === "approvals" ? `Approvals${actions.length ? ` (${actions.length})` : ""}` : t === "today" ? "Today" : "Calls"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === "today" && (
        <FlatList
          data={day?.entries || []}
          keyExtractor={(e) => `${e.kind}-${e.id}`}
          ListHeaderComponent={<Text style={{ color: theme.textMuted, padding: 16, fontSize: 13 }}>{day?.headline || ""}</Text>}
          ListEmptyComponent={<Text style={[styles.empty, { color: theme.textMuted }]}>Nothing yet today.</Text>}
          renderItem={({ item: e }) => (
            <TouchableOpacity
              onPress={() => (e.kind === "meeting" ? router.push(`/call/${e.id}`) : e.status === "proposed" ? setTab("approvals") : null)}
              style={[styles.row2, { borderBottomColor: theme.border }]}>
              <Text>{DAY_ICON[e.kind] || (e.status === "executed" ? "✅" : "📝")}</Text>
              <View style={{ flex: 1 }}>
                <Text style={{ color: theme.text, fontSize: 14 }} numberOfLines={2}>{e.title}</Text>
                <Text style={{ color: theme.textMuted, fontSize: 12 }}>
                  {new Date(e.at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                  {e.status === "proposed" ? " · needs you" : ""}{e.score != null ? ` · ${e.score}/100` : ""}
                </Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}

      {tab === "calls" && (
        <FlatList
          data={calls}
          keyExtractor={(m) => String(m.id)}
          ListEmptyComponent={<Text style={[styles.empty, { color: theme.textMuted }]}>No calls yet. Ask your coworker in chat to join one.</Text>}
          renderItem={({ item: m }) => (
            <TouchableOpacity onPress={() => router.push(`/call/${m.id}`)} style={[styles.row2, { borderBottomColor: theme.border }]}>
              <Text>📞</Text>
              <View style={{ flex: 1 }}>
                <Text style={{ color: theme.text, fontSize: 14 }} numberOfLines={1}>{m.title}</Text>
                <Text style={{ color: m.status === "active" ? "#10B981" : theme.textMuted, fontSize: 12 }}>
                  {m.status === "active" ? "● Live now" : `Ended${m.summary?.score != null ? ` · ${m.summary.score}/100` : ""}`}
                </Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}

      {tab !== "approvals" ? null : !status.exists ? (
        <Text style={[styles.empty, { color: theme.textMuted }]}>Set up your coworker on the web app first.</Text>
      ) : (
        <FlatList
          data={actions}
          keyExtractor={(a) => String(a.id)}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}
          ListHeaderComponent={
            <View style={{ padding: 16 }}>
              {paused && <Text style={[styles.banner]}>Paused. Nothing will be sent until you resume.</Text>}
              {!!headline && <Text style={{ color: theme.textMuted, fontSize: 13 }}>{headline}</Text>}
              <Text style={[styles.section, { color: theme.text }]}>Waiting for you ({actions.length})</Text>
            </View>
          }
          ListEmptyComponent={<Text style={[styles.empty, { color: theme.textMuted }]}>You're all caught up.</Text>}
          renderItem={({ item: a }) => (
            <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <Text style={[styles.cardTitle, { color: theme.text }]}>{ICON[a.type] || "⚙️"} {a.title}</Text>
              {a.type === "email.send" && (
                <Text style={{ color: theme.textMuted, fontSize: 12, marginTop: 2 }}>To {(a.payload.to || []).join(", ")}</Text>
              )}
              {editing === a.id ? (
                <TextInput
                  multiline
                  value={draft}
                  onChangeText={setDraft}
                  style={[styles.input, { color: theme.text, borderColor: theme.border }]}
                />
              ) : (
                <Text style={{ color: theme.text, fontSize: 14, marginTop: 8 }} numberOfLines={8}>
                  {a.payload.body || a.payload.text || a.payload.description || a.reasoning}
                </Text>
              )}
              {a.risks.map((r) => (
                <Text key={r.code} style={styles.risk}>⚠ {r.message}</Text>
              ))}
              <View style={styles.row}>
                <TouchableOpacity style={[styles.btn, { backgroundColor: theme.sendButton }]} onPress={() => approve(a)} disabled={paused}>
                  <Text style={{ color: theme.sendButtonText, fontWeight: "600" }}>
                    {a.type === "responsibility.create" ? "Confirm" : "Approve"}
                  </Text>
                </TouchableOpacity>
                {(a.type === "email.send" || a.type === "slack.post") && (
                  <TouchableOpacity
                    style={[styles.btn, { borderColor: theme.border, borderWidth: 1 }]}
                    onPress={() => { setEditing(editing === a.id ? null : a.id); setDraft(a.payload.body || a.payload.text || ""); }}
                  >
                    <Text style={{ color: theme.text }}>{editing === a.id ? "Cancel" : "Edit"}</Text>
                  </TouchableOpacity>
                )}
                <TouchableOpacity style={[styles.btn, { borderColor: theme.border, borderWidth: 1 }]} onPress={() => reject(a)}>
                  <Text style={{ color: theme.text }}>Reject</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 12, paddingVertical: 10, borderBottomWidth: 1 },
  headerBtn: { padding: 8 },
  title: { fontSize: 16, fontWeight: "600" },
  kill: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  banner: { backgroundColor: "#FEF3C7", color: "#92400E", padding: 10, borderRadius: 8, marginBottom: 8, fontSize: 13 },
  section: { fontSize: 15, fontWeight: "600", marginTop: 12 },
  empty: { textAlign: "center", marginTop: 40, fontSize: 14 },
  card: { marginHorizontal: 16, marginBottom: 12, padding: 14, borderRadius: 12, borderWidth: 1 },
  cardTitle: { fontSize: 14, fontWeight: "600" },
  risk: { color: "#B45309", fontSize: 12, marginTop: 6 },
  input: { borderWidth: 1, borderRadius: 8, padding: 8, marginTop: 8, minHeight: 120, textAlignVertical: "top" },
  row: { flexDirection: "row", gap: 8, marginTop: 12 },
  btn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8 },
  tabs: { flexDirection: "row", borderBottomWidth: 1 },
  tab: { flex: 1, alignItems: "center", paddingVertical: 10, borderBottomWidth: 2, borderBottomColor: "transparent" },
  row2: { flexDirection: "row", gap: 10, alignItems: "center", paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1 },
});
