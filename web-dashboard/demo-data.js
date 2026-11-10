/* Demo dataset — realistic sample memories so the dashboard works fully
   offline on GitHub Pages (demo mode). Live mode fetches from dreamcore. */

window.DEMO_SOURCES = [
  { id: "gmail", label: "Gmail", description: "Email messages (readonly scope)",
    requires_google_auth: true, options: { query: "in:inbox OR in:sent", max_results: 500 } },
  { id: "calendar", label: "Google Calendar", description: "Events ±365 days (readonly scope)",
    requires_google_auth: true, options: { calendar_id: "primary", past_days: 365, future_days: 365, max_results: 2500 } },
  { id: "photos", label: "Google Photos", description: "Photo metadata via Picker API (no image download)",
    requires_google_auth: true, options: { max_items: 10000 } },
  { id: "browser", label: "Browser history", description: "Chrome/Chromium + Firefox visited pages",
    requires_google_auth: false, options: { which: null, max_results: 20000 } },
  { id: "files", label: "Local files", description: "Text-readable files in a directory (chunked)",
    requires_google_auth: false, options: { path: ".", max_files: 5000 } }
];

window.DEMO = {
  stats: { total: 1284, bySource: { whatsapp: 742, discord: 431, gmail: 111 }, lastIngest: "2026-11-10T22:14:00Z" },
  memories: [
    { id: "d1", title: "Family · Alice", sender: "Alice", chat: "Family", source: "whatsapp", ts: "2026-11-08T19:22:00Z",
      text: "Don't forget dinner at Luigi's on Friday — mom is making her famous lasagna and uncle Ray is driving up from Sacramento." },
    { id: "d2", title: "Work · Priya", sender: "Priya", chat: "Launch Team", source: "discord", ts: "2026-11-09T14:03:00Z",
      text: "Staging deploy is green. The memory indexer handles about 40 docs/sec on the M-series laptop — good enough for personal scale." },
    { id: "d3", title: "Friends · Marco", sender: "Marco", chat: "Weekend Crew", source: "whatsapp", ts: "2026-11-07T21:40:00Z",
      text: "That ramen place on 5th finally got a reservation for 4 — you owe me one after the fantasy league debacle." },
    { id: "d4", title: "Work · Sam", sender: "Sam", chat: "#backend", source: "discord", ts: "2026-11-06T09:15:00Z",
      text: "The receipt PDF you asked about is in the shared drive under /finance/2026/oct — file name starts with INV-2291." },
    { id: "d5", title: "Mom · Mom", sender: "Mom", chat: "Family", source: "whatsapp", ts: "2026-11-05T17:55:00Z",
      text: "Call the dentist on Tuesday to reschedule. They moved us to 3:30pm. Also your grandma's birthday card is in the blue folder." },
    { id: "d6", title: "Gym · Coach Dana", sender: "Coach Dana", chat: "Gym", source: "whatsapp", ts: "2026-11-04T08:10:00Z",
      text: "New program starts Monday: 4 days strength, Wednesday is zone-2 cardio. Bring the heart-rate strap." },
    { id: "d7", title: "Friends · Lena", sender: "Lena", chat: "Book Club", source: "discord", ts: "2026-11-03T20:30:00Z",
      text: "This month's pick is 'The Creative Act' — chapter 4 discussion is where everyone disagrees, come ready." },
    { id: "d8", title: "Bank · Alerts", sender: "Alerts", chat: "Finance", source: "gmail", ts: "2026-11-02T13:00:00Z",
      text: "Your November statement is ready. Autopay for the credit card is scheduled for the 15th." },
    { id: "d9", title: "Friends · Marco", sender: "Marco", chat: "Weekend Crew", source: "whatsapp", ts: "2026-10-30T22:05:00Z",
      text: "Photos from the hike are in the shared album — the one at the waterfall at mile 6 is the keeper." },
    { id: "d10", title: "Work · Jira Bot", sender: "Jira Bot", chat: "#alerts", source: "discord", ts: "2026-10-29T11:45:00Z",
      text: "Issue IDP-4412 'password reset loop on SSO' moved to Done. Root cause was a stale session cookie." },
    { id: "d11", title: "Landlord · Mr. Okafor", sender: "Mr. Okafor", chat: "Apartment", source: "gmail", ts: "2026-10-28T16:20:00Z",
      text: "Reminder: furnace inspection is scheduled for the 12th between 9am–12pm. Please ensure access to the utility room." },
    { id: "d12", title: "Mom · Mom", sender: "Mom", chat: "Family", source: "whatsapp", ts: "2026-10-27T09:00:00Z",
      text: "Your sister's graduation is May 18th — save the date. She wants you to give a short speech this time." }
  ],
  graph: {
    nodes: [
      { id: "Family", group: 1 }, { id: "Launch Team", group: 1 }, { id: "Weekend Crew", group: 1 },
      { id: "#backend", group: 1 }, { id: "#alerts", group: 1 }, { id: "Gym", group: 1 },
      { id: "Book Club", group: 1 }, { id: "Finance", group: 1 }, { id: "Apartment", group: 1 },
      { id: "Alice", group: 2 }, { id: "Priya", group: 2 }, { id: "Marco", group: 2 },
      { id: "Sam", group: 2 }, { id: "Mom", group: 2 }, { id: "Coach Dana", group: 2 },
      { id: "Lena", group: 2 }, { id: "Alerts", group: 2 }, { id: "Jira Bot", group: 2 },
      { id: "Mr. Okafor", group: 2 }
    ],
    edges: [
      { source: "Family", target: "Alice", value: 2 }, { source: "Family", target: "Mom", value: 2 },
      { source: "Launch Team", target: "Priya", value: 1 }, { source: "Weekend Crew", target: "Marco", value: 2 },
      { source: "#backend", target: "Sam", value: 1 }, { source: "#alerts", target: "Jira Bot", value: 1 },
      { source: "Gym", target: "Coach Dana", value: 1 }, { source: "Book Club", target: "Lena", value: 1 },
      { source: "Finance", target: "Alerts", value: 1 }, { source: "Apartment", target: "Mr. Okafor", value: 1 }
    ]
  }
};
