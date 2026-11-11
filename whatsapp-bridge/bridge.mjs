#!/usr/bin/env node
/**
 * Internet's Dream — WhatsApp bridge (Baileys / WhatsApp Web).
 *
 * Links your real WhatsApp account via QR scan (multi-device), then
 * forwards every incoming message to `dream serve` (/ingest-text) so it
 * lands encrypted in your memory store.
 *
 * READ-ONLY BY DEFAULT: this bridge never sends messages. It only
 * receives and indexes. Set SEND_READ_RECEIPTS=1 to mark messages read.
 *
 * Usage:
 *   node bridge.mjs                 # uses http://127.0.0.1:8765
 *   API_BASE=http://host:8765 node bridge.mjs
 *   SEND_READ_RECEIPTS=1 node bridge.mjs
 */

import * as baileys from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import pino from 'pino';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

const API_BASE = (process.env.API_BASE || 'http://127.0.0.1:8765').replace(/\/$/, '');
const AUTH_DIR = join(homedir(), '.internet-dream', 'whatsapp-auth');
const INBOX_DIR = join(homedir(), '.internet-dream', 'whatsapp-media');
const SEND_READ_RECEIPTS = process.env.SEND_READ_RECEIPTS === '1';

mkdirSync(AUTH_DIR, { recursive: true });
mkdirSync(INBOX_DIR, { recursive: true });

const logger = pino({ level: process.env.LOG_LEVEL || 'warn' });

async function post(doc) {
  try {
    const r = await fetch(`${API_BASE}/ingest-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(doc),
    });
    if (!r.ok) logger.warn(`ingest ${r.status}: ${await r.text()}`);
  } catch (e) {
    logger.warn(`ingest failed (is dream serve running?): ${e.message}`);
  }
}

function msgText(msg) {
  const m = msg.message || {};
  return (
    m.conversation ||
    m.extendedTextMessage?.text ||
    m.imageMessage?.caption ||
    m.videoMessage?.caption ||
    ''
  );
}

const {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  downloadMediaMessage,
} = baileys;

async function start() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();
  const sock = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: false,
    browser: ['Internet\'s Dream', 'Chrome', '1.0'],
    markOnlineOnConnect: false,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (u) => {
    if (u.qr) {
      console.log('\n📱 Scan this QR with WhatsApp → Linked Devices:\n');
      qrcode.generate(u.qr, { small: true });
      writeFileSync(join(AUTH_DIR, 'last-qr.txt'), u.qr);
    }
    if (u.connection === 'open') {
      console.log(`\n✅ WhatsApp connected as ${sock.user?.id}. Indexing incoming messages → ${API_BASE}`);
    }
    if (u.connection === 'close') {
      const code = u.lastDisconnect?.error?.output?.statusCode;
      if (code !== DisconnectReason.loggedOut) {
        console.log('Connection closed — reconnecting…');
        setTimeout(start, 3000);
      } else {
        console.log('Logged out. Delete ~/.internet-dream/whatsapp-auth to re-link.');
        process.exit(1);
      }
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const msg of messages) {
      if (msg.key.fromMe) continue; // don't index our own outgoing msgs twice
      const jid = msg.key.remoteJid;
      if (!jid || jid === 'status@broadcast') continue;

      const isGroup = jid.endsWith('@g.us');
      const senderJid = msg.key.participant || jid;
      let chatName = jid;
      let senderName = senderJid.split('@')[0];
      try {
        if (isGroup) {
          const meta = await sock.groupMetadata(jid);
          chatName = meta.subject;
          const pn = meta.participants?.find((p) => p.id === senderJid);
          senderName = pn?.notify || pn?.name || senderName;
        } else {
          const cn = await sock.onWhatsApp(jid);
          if (cn?.[0]?.name) senderName = cn[0].name;
          chatName = senderName;
        }
      } catch { /* names optional */ }

      const text = msgText(msg).trim();
      const hasMedia = !!(msg.message?.imageMessage || msg.message?.videoMessage ||
                          msg.message?.documentMessage || msg.message?.audioMessage);
      if (!text && !hasMedia) continue;

      let mediaNote = '';
      if (hasMedia) {
        try {
          const buf = await downloadMediaMessage(msg, 'buffer', {});
          const ext = msg.message.imageMessage ? 'jpg'
            : msg.message.videoMessage ? 'mp4'
            : msg.message.audioMessage ? 'ogg' : 'bin';
          const fname = join(INBOX_DIR, `${msg.key.id || Date.now()}.${ext}`);
          writeFileSync(fname, buf);
          mediaNote = `\n[media saved: ${fname}]`;
        } catch (e) {
          mediaNote = '\n[media download failed]';
        }
      }

      await post({
        source: 'whatsapp',
        title: `${isGroup ? chatName : senderName}`,
        text: `${senderName}: ${text}${mediaNote}`,
        sender: senderName,
        chat: chatName,
        ts: msg.messageTimestamp
          ? Number(msg.messageTimestamp)
          : Date.now() / 1000,
      });

      if (SEND_READ_RECEIPTS) {
        try { await sock.readMessages([msg.key]); } catch {}
      }
    }
  });
}

start().catch((e) => { console.error(e); process.exit(1); });
