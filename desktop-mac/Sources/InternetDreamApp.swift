// Internet's Dream — macOS client (SwiftUI, Liquid Glass design)
// Thin client for `dreamcore serve` on http://127.0.0.1:8765.
// Build: scripts/build-mac-dmg.sh  (runs on macOS CI runner)

import SwiftUI

@main
struct InternetDreamApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 900, minHeight: 640)
        }
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unified(showsTitle: false))
    }
}

struct MemoryHit: Decodable, Identifiable {
    let doc_id: String
    let score: Double
    let title: String
    let sender: String?
    let chat: String?
    let source: String
    let snippet: String?
    var id: String { doc_id }
}

struct Stats: Decodable {
    let total: Int
    let by_source: [String: Int]?
    let by_kind: [String: Int]?
}

struct AskResponse: Decodable {
    let answer: String
}

@MainActor
final class DreamStore: ObservableObject {
    @Published var apiBase = "http://127.0.0.1:8765"
    @Published var stats: Stats?
    @Published var online = false
    @Published var results: [MemoryHit] = []
    @Published var answer = ""
    @Published var query = ""

    func get<T: Decodable>(_ path: String, as: T.Type) async throws -> T {
        let (data, resp) = try await URLSession.shared.data(from: URL(string: apiBase + path)!)
        guard (resp as? HTTPURLResponse)?.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    func post(_ path: String, json: [String: String]) async throws -> AskResponse {
        var req = URLRequest(url: URL(string: apiBase + path)!)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: json)
        let (data, resp) = try await URLSession.shared.data(for: req)
        guard (resp as? HTTPURLResponse)?.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(AskResponse.self, from: data)
    }

    func refresh() async {
        do {
            stats = try await get("/stats", as: Stats.self)
            online = true
        } catch {
            online = false
        }
    }

    func search() async {
        guard !query.isEmpty else { return }
        let enc = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        results = (try? await get("/search?q=\(enc)&limit=20", as: [MemoryHit].self)) ?? []
    }

    func ask() async {
        guard !query.isEmpty else { return }
        answer = "Thinking…"
        answer = (try? await post("/ask", json: ["question": query]))?.answer ?? "backend offline — run `dream serve`"
    }
}

// MARK: - Liquid Glass primitives

struct GlassCard<Content: View>: View {
    let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }
    var body: some View {
        content
            .padding(18)
            .background {
                if #available(macOS 26.0, *) {
                    Color.clear.glassEffect(.regular, in: .rect(cornerRadius: 20))
                } else {
                    RoundedRectangle(cornerRadius: 20).fill(.ultraThinMaterial)
                }
            }
    }
}

struct PillButton: View {
    let title: String
    let action: () -> Void
    var body: some View {
        Group {
            if #available(macOS 26.0, *) {
                Button(action: action) {
                    Text(title).font(.headline).padding(.horizontal, 18).padding(.vertical, 9)
                }
                .buttonStyle(.glass)
                .tint(.purple)
            } else {
                Button(action: action) {
                    Text(title).font(.headline).padding(.horizontal, 18).padding(.vertical, 9)
                }
                .buttonStyle(.borderedProminent)
                .tint(.purple)
            }
        }
    }
}

// MARK: - Views

struct ContentView: View {
    @StateObject private var store = DreamStore()
    @State private var tab = 0

    var body: some View {
        NavigationSplitView {
            List(selection: $tab) {
                Label("Dashboard", systemImage: "rectangle.3.group").tag(0)
                Label("Search", systemImage: "magnifyingglass").tag(1)
                Label("Ask", systemImage: "questionmark.bubble").tag(2)
                Label("Settings", systemImage: "gear").tag(3)
            }
            .navigationTitle("Internet's Dream")
        } detail: {
            Group {
                switch tab {
                case 0: DashboardView(store: store)
                case 1: SearchView(store: store)
                case 2: AskView(store: store)
                default: SettingsView(store: store)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(24)
            .background(LinearGradient(
                colors: [.purple.opacity(0.12), .blue.opacity(0.08), .clear],
                startPoint: .topLeading, endPoint: .bottomTrailing))
        }
        .task { await store.refresh() }
    }
}

struct DashboardView: View {
    @ObservedObject var store: DreamStore
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Your digital life, indexed locally.")
                    .font(.title2.weight(.semibold))
                HStack(spacing: 14) {
                    GlassCard {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Memories").font(.caption).foregroundStyle(.secondary)
                            Text("\(store.stats?.total ?? 0)")
                                .font(.system(size: 34, weight: .medium))
                        }
                    }
                    GlassCard {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Backend").font(.caption).foregroundStyle(.secondary)
                            Text(store.online ? "Connected" : "Offline")
                                .font(.title3.weight(.semibold))
                                .foregroundStyle(store.online ? .green : .orange)
                        }
                    }
                }
                GlassCard {
                    Text("AES-256-GCM encrypted at rest · zero telemetry · all data stays on this Mac.")
                        .font(.callout).foregroundStyle(.secondary)
                }
            }
        }
    }
}

struct SearchView: View {
    @ObservedObject var store: DreamStore
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Search memories").font(.title2.weight(.semibold))
            HStack {
                TextField("e.g. restaurant recommendation last month…", text: $store.query)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit { Task { await store.search() } }
                PillButton(title: "Search") { Task { await store.search() } }
            }
            ScrollView {
                LazyVStack(spacing: 10) {
                    ForEach(store.results) { h in
                        GlassCard {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(h.title).font(.headline)
                                Text("\(h.sender ?? "unknown") · \(h.source)")
                                    .font(.caption).foregroundStyle(.secondary)
                                Text(h.snippet ?? "").font(.callout)
                                    .foregroundStyle(.secondary).lineLimit(3)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
            }
        }
    }
}

struct AskView: View {
    @ObservedObject var store: DreamStore
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Ask your second brain").font(.title2.weight(.semibold))
            HStack {
                TextField("What was that restaurant my friend recommended?", text: $store.query)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit { Task { await store.ask() } }
                PillButton(title: "Ask") { Task { await store.ask() } }
            }
            ScrollView {
                GlassCard {
                    Text(store.answer.isEmpty ? "Answers are grounded in your indexed memories and cite sources." : store.answer)
                        .font(.body).textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }
}

struct SettingsView: View {
    @ObservedObject var store: DreamStore
    @State private var base = ""
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Settings").font(.title2.weight(.semibold))
            GlassCard {
                VStack(alignment: .leading, spacing: 10) {
                    Text("dreamcore API").font(.headline)
                    TextField("API base URL", text: $base)
                        .textFieldStyle(.roundedBorder)
                    PillButton(title: "Save & reconnect") {
                        if !base.isEmpty { store.apiBase = base }
                        Task { await store.refresh() }
                    }
                    Text("Backend: \(store.apiBase) — \(store.online ? "connected" : "offline")")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            GlassCard {
                Text("Configure the LLM gateway on the backend:\n\n  dream config --provider openai-compatible \\\n    --base-url https://api.openai.com/v1 \\\n    --api-key sk-... --model gpt-4o-mini")
                    .font(.system(.callout, design: .monospaced))
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            }
        }
        .onAppear { base = store.apiBase }
    }
}
