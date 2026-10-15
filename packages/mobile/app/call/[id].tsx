import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert, FlatList, KeyboardAvoidingView, Linking, Platform, SafeAreaView, StyleSheet, Text, TextInput, TouchableOpacity, View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useAppTheme } from "../_layout";
import { Meeting, endMeeting, getMeeting, whisper } from "../../src/api";

const POLL_MS = 3000;

/** Follow a call your coworker is taking: live transcript, whisper an instruction, or take over. */
export default function CallScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { theme } = useAppTheme();
  const [m, setM] = useState<Meeting | null>(null);
  const [note, setNote] = useState("");
  const listRef = useRef<FlatList>(null);

  const load = useCallback(async () => {
    try { setM(await getMeeting(Number(id))); } catch {}
  }, [id]);

  useEffect(() => {
    load();
    const t = setInterval(() => { if (!m || m.status === "active") load(); }, POLL_MS);
    return () => clearInterval(t);
  }, [load, m?.status]);

  const live = m?.status === "active";
  const sendWhisper = async () => {
    if (!note.trim()) return;
    const text = note.trim();
    setNote("");
    setM(await whisper(Number(id), text));
  };
  const takeOver = () => {
    Alert.alert("Take over?", "Your coworker will leave the call and write up what happened so far.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Take over", style: "destructive", onPress: async () => {
          const url = m?.meetingUrl;
          setM(await endMeeting(Number(id)));
          if (url) Linking.openURL(url);
        },
      },
    ]);
  };

  const who = (speaker: string) => (speaker === "coworker" ? "Your AI coworker" : speaker === "owner" ? "You (whisper)" : m?.prospectName || "Them");

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity onPress={() => router.back()} style={{ padding: 8 }}>
          <Text style={{ color: theme.text, fontSize: 16 }}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={[styles.title, { color: theme.text }]} numberOfLines={1}>{m?.title || "Call"}</Text>
        <Text style={{ color: live ? "#10B981" : theme.textMuted, fontSize: 12, padding: 8 }}>{live ? "● Live" : "Ended"}</Text>
      </View>
      {m?.metrics?.consent === "pending" && (
        <Text style={[styles.banner, { backgroundColor: theme.surfaceAlt, color: theme.textMuted }]}>
          Notes are off until they agree. Their words aren't saved until then.
        </Text>
      )}
      <FlatList
        ref={listRef}
        data={[...(m?.transcript || []), ...((m as any)?.whispers || [])].sort((a, b) => String(a.at || "").localeCompare(String(b.at || "")))}
        keyExtractor={(_, i) => String(i)}
        contentContainerStyle={{ padding: 12 }}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        renderItem={({ item }) => (
          <View style={[styles.turn, { alignSelf: item.speaker === "coworker" ? "flex-start" : "flex-end",
            backgroundColor: item.speaker === "coworker" ? theme.surface : item.speaker === "owner" ? theme.surfaceAlt : theme.userBubble }]}>
            <Text style={{ color: theme.textMuted, fontSize: 11 }}>{who(item.speaker)}{item.kind && item.kind !== "agent" ? ` · ${item.kind}` : ""}</Text>
            <Text style={{ color: theme.text, fontSize: 14, fontStyle: item.redacted ? "italic" : "normal" }}>
              {item.redacted ? "Not recorded (no consent yet)" : item.text}
            </Text>
          </View>
        )}
        ListFooterComponent={!live && m?.summary?.text ? (
          <View style={[styles.summary, { borderColor: theme.border }]}>
            <Text style={{ color: theme.text, fontWeight: "600" }}>Summary{m.summary.score != null ? ` · ${m.summary.score}/100` : ""}</Text>
            <Text style={{ color: theme.text, marginTop: 6 }}>{m.summary.text}</Text>
          </View>
        ) : null}
      />
      {live && (
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
          <View style={[styles.controls, { borderTopColor: theme.border }]}>
            <TextInput value={note} onChangeText={setNote} onSubmitEditing={sendWhisper}
              placeholder="Whisper to your coworker (only it sees this)" placeholderTextColor={theme.textMuted}
              style={[styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.inputBg }]} />
            <View style={{ flexDirection: "row", gap: 8, marginTop: 8 }}>
              <TouchableOpacity style={[styles.btn, { backgroundColor: theme.sendButton }]} onPress={sendWhisper}>
                <Text style={{ color: theme.sendButtonText, fontWeight: "600" }}>Whisper</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, { borderWidth: 1, borderColor: theme.border }]} onPress={takeOver}>
                <Text style={{ color: theme.text }}>Take over</Text>
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 8, paddingVertical: 8, borderBottomWidth: 1 },
  title: { flex: 1, textAlign: "center", fontSize: 15, fontWeight: "600" },
  banner: { margin: 12, marginBottom: 0, padding: 10, borderRadius: 8, fontSize: 12 },
  turn: { maxWidth: "85%", borderRadius: 14, padding: 10, marginBottom: 8 },
  summary: { borderWidth: 1, borderRadius: 12, padding: 12, marginTop: 8 },
  controls: { borderTopWidth: 1, padding: 12 },
  input: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 8, fontSize: 14 },
  btn: { paddingHorizontal: 16, paddingVertical: 9, borderRadius: 8 },
});
