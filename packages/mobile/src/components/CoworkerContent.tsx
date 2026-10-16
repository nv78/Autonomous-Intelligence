import React, { useEffect, useState } from "react";
import { Text, TouchableOpacity, View, StyleSheet } from "react-native";
import { router } from "expo-router";
import { CoworkerAction, Meeting, approveAction, getActions, getMeeting, rejectAction } from "../api";
import { parseSegments } from "../markers";
import { Theme } from "../theme";

function ActionInline({ id, theme }: { id: number; theme: Theme }) {
  const [a, setA] = useState<CoworkerAction | null>(null);
  useEffect(() => { getActions([id]).then((r) => setA(r[0] || null)).catch(() => {}); }, [id]);
  if (!a) return null;
  const p = a.payload || {};
  const pending = a.status === "proposed";
  return (
    <View style={[styles.card, { borderColor: theme.border, backgroundColor: theme.surface }]}>
      <Text style={[styles.title, { color: theme.text }]}>{a.title}</Text>
      {!!p.to && <Text style={{ color: theme.textMuted, fontSize: 12 }}>To {(p.to || []).join(", ")}</Text>}
      <Text style={{ color: theme.text, fontSize: 13, marginTop: 6 }} numberOfLines={6}>{p.body || p.text || a.reasoning}</Text>
      {pending ? (
        <View style={styles.row}>
          <TouchableOpacity style={[styles.btn, { backgroundColor: theme.sendButton }]}
            onPress={async () => setA(await approveAction(a.id))}>
            <Text style={{ color: theme.sendButtonText, fontWeight: "600" }}>Approve</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.btn, { borderWidth: 1, borderColor: theme.border }]}
            onPress={async () => setA(await rejectAction(a.id))}>
            <Text style={{ color: theme.text }}>Reject</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <Text style={{ color: theme.textMuted, fontSize: 12, marginTop: 6 }}>{a.status === "executed" ? "✓ Done" : a.status}</Text>
      )}
    </View>
  );
}

function MeetingInline({ id, theme }: { id: number; theme: Theme }) {
  const [m, setM] = useState<Meeting | null>(null);
  useEffect(() => { getMeeting(id).then(setM).catch(() => {}); }, [id]);
  if (!m) return null;
  const live = m.status === "active";
  return (
    <TouchableOpacity onPress={() => router.push(`/call/${m.id}`)}
      style={[styles.card, { borderColor: theme.border, backgroundColor: theme.surface }]}>
      <Text style={[styles.title, { color: theme.text }]}>📞 {m.title}</Text>
      <Text style={{ color: theme.textMuted, fontSize: 12, marginTop: 2 }}>
        {live ? "● Live · tap to watch, whisper, or take over" : `Ended${m.summary?.score != null ? ` · lead score ${m.summary.score}/100` : ""} · tap for transcript`}
      </Text>
    </TouchableOpacity>
  );
}

/** A coworker reply: text, tool chips, and inline approval / call cards. */
export default function CoworkerContent({ content, theme }: { content: string; theme: Theme }) {
  return (
    <View>
      {parseSegments(content).map((seg, i) => {
        if (seg.kind === "text") return <Text key={i} style={{ color: theme.text, fontSize: 14, lineHeight: 20 }}>{seg.text}</Text>;
        if (seg.kind === "tool") return <Text key={i} style={{ color: theme.textMuted, fontSize: 12, marginVertical: 2 }}>✓ {seg.summary}</Text>;
        if (seg.kind === "action") return <ActionInline key={i} id={seg.id} theme={theme} />;
        return <MeetingInline key={i} id={seg.id} theme={theme} />;
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: 12, padding: 12, marginVertical: 6 },
  title: { fontSize: 14, fontWeight: "600" },
  row: { flexDirection: "row", gap: 8, marginTop: 10 },
  btn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8 },
});
