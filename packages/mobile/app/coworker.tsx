import React, { useCallback, useEffect, useState } from "react";
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet, SafeAreaView, TextInput, RefreshControl, Alert,
} from "react-native";
import { router } from "expo-router";
import { useAppTheme } from "./_layout";
import {
  CoworkerAction, approveAction, getCoworkerStatus, getDigest, getPendingActions, rejectAction, setCoworkerPaused,
  tickCoworker,
} from "../src/api";

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

  const load = useCallback(async () => {
    try {
      await tickCoworker().catch(() => {});
      const [s, a, d] = await Promise.all([getCoworkerStatus(), getPendingActions(), getDigest().catch(() => null)]);
      setStatus(s);
      setActions(a);
      if (d) setHeadline(d.headline);
    } catch {}
  }, []);

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

      {!status.exists ? (
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
});
