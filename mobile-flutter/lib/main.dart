// Internet's Dream — Flutter mobile client (Material 3 Expressive)
// Thin shell over `dream serve` — all features live in the backend.

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() => runApp(const DreamApp());

// ---------- API client ----------
class Api {
  static String base = 'http://10.0.2.2:8765'; // Android emulator → host loopback

  static Future<dynamic> get(String path) async {
    final r = await http.get(Uri.parse('$base$path'));
    if (r.statusCode != 200) throw Exception('${r.statusCode} ${r.reasonPhrase}');
    return jsonDecode(r.body);
  }

  static Future<dynamic> post(String path, Map<String, dynamic> body) async {
    final r = await http.post(Uri.parse('$base$path'),
        headers: {'Content-Type': 'application/json'}, body: jsonEncode(body));
    if (r.statusCode != 200) {
      String detail = r.reasonPhrase ?? 'error';
      try { detail = jsonDecode(r.body)['detail'] ?? detail; } catch (_) {}
      throw Exception('$detail');
    }
    return jsonDecode(r.body);
  }
}

// ---------- theme: Material 3 Expressive ----------
ThemeData dreamTheme(Brightness b) {
  final scheme = ColorScheme.fromSeed(
    seedColor: const Color(0xFF6D4BD8),
    brightness: b,
    primary: b == Brightness.light ? const Color(0xFF6D4BD8) : const Color(0xFFD6BCFF),
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: scheme.surface,
    appBarTheme: AppBarTheme(
      centerTitle: false,
      elevation: 0,
      backgroundColor: scheme.surface.withValues(alpha: .85),
      titleTextStyle: TextStyle(
        fontSize: 24, fontWeight: FontWeight.w800, letterSpacing: -.4,
        color: scheme.onSurface,
      ),
    ),
    cardTheme: CardThemeData(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      color: scheme.surfaceContainerLow,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: const StadiumBorder(),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      height: 72,
      labelTextStyle: WidgetStatePropertyAll(
        TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
      iconTheme: WidgetStateProperty.resolveWith((states) => IconThemeData(
        size: 26,
        color: states.contains(WidgetState.selected)
            ? scheme.primary : scheme.onSurfaceVariant,
      )),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surfaceContainerHigh,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(20),
        borderSide: BorderSide.none,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(20),
        borderSide: BorderSide(color: scheme.primary, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
    ),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
  );
}

class DreamApp extends StatelessWidget {
  const DreamApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: "Internet's Dream",
        debugShowCheckedModeBanner: false,
        theme: dreamTheme(Brightness.light),
        darkTheme: dreamTheme(Brightness.dark),
        themeMode: ThemeMode.system,
        home: const HomePage(),
      );
}

// ---------- shared widgets ----------
class StatCard extends StatelessWidget {
  final String label, value, sub;
  const StatCard(this.label, this.value, this.sub, {super.key});
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label.toUpperCase(), style: TextStyle(
            fontSize: 11, fontWeight: FontWeight.w800,
            letterSpacing: 1, color: cs.onSurfaceVariant)),
          const SizedBox(height: 8),
          Text(value, style: TextStyle(
            fontSize: 32, fontWeight: FontWeight.w800,
            color: cs.primary, letterSpacing: -1)),
          const SizedBox(height: 4),
          Text(sub, style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
        ]),
      ),
    );
  }
}

class MemTile extends StatelessWidget {
  final Map<String, dynamic> m;
  const MemTile(this.m, {super.key});
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final sender = (m['sender'] ?? '').toString();
    final title = (m['title'] ?? '').toString();
    final text = (m['snippet'] ?? m['text'] ?? '').toString();
    final source = (m['source'] ?? '').toString();
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: CircleAvatar(
          backgroundColor: cs.primaryContainer,
          child: Text(
            (sender.isEmpty ? title : sender).substring(0, 1).toUpperCase(),
            style: TextStyle(color: cs.onPrimaryContainer, fontWeight: FontWeight.w800),
          ),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
        subtitle: Text(
          '${sender.isEmpty ? source : sender} · ${text.length > 140 ? '${text.substring(0, 140)}…' : text}',
          maxLines: 2, overflow: TextOverflow.ellipsis,
          style: TextStyle(color: cs.onSurfaceVariant, fontSize: 13),
        ),
      ),
    );
  }
}

// ---------- pages ----------
class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});
  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Map<String, dynamic>? stats;
  List<dynamic> recent = [];
  String? error;

  @override
  void initState() { super.initState(); load(); }

  Future<void> load() async {
    try {
      final s = await Api.get('/stats');
      final r = await Api.get('/search?q=the&limit=5');
      setState(() { stats = Map<String, dynamic>.from(s); recent = r; error = null; });
    } catch (e) {
      setState(() { error = '$e'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text("Dashboard")),
      body: RefreshIndicator(
        onRefresh: load,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            Text("Your digital life, indexed locally.",
                style: TextStyle(color: cs.onSurfaceVariant, fontSize: 14)),
            const SizedBox(height: 18),
            if (error != null)
              Card(child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text("Offline — start `dream serve`.\n$error",
                    style: TextStyle(color: cs.error)),
              )),
            if (stats != null) ...[
              GridView.count(
                crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 12, crossAxisSpacing: 12, childAspectRatio: 1.5,
                children: [
                  StatCard('Memories', '${stats!['total']}', 'encrypted · AES-256-GCM'),
                  ...((stats!['by_source'] as Map?)?.entries ?? const Iterable<MapEntry<String, dynamic>>.empty())
                      .take(3)
                      .map((e) => StatCard(e.key, '${e.value}', 'indexed documents')),
                ],
              ),
              const SizedBox(height: 20),
            ],
            Text('RECENT MEMORIES', style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1,
              color: cs.onSurfaceVariant)),
            const SizedBox(height: 8),
            ...recent.map((m) => MemTile(Map<String, dynamic>.from(m as Map))),
          ],
        ),
      ),
    );
  }
}

class SearchPage extends StatefulWidget {
  const SearchPage({super.key});
  @override
  State<SearchPage> createState() => _SearchPageState();
}

class _SearchPageState extends State<SearchPage> {
  final q = TextEditingController();
  List<dynamic> hits = [];
  bool loading = false;
  String? error;

  Future<void> run() async {
    final query = q.text.trim();
    if (query.isEmpty) return;
    setState(() { loading = true; error = null; });
    try {
      final r = await Api.get('/search?q=${Uri.encodeComponent(query)}&limit=20');
      setState(() { hits = r; loading = false; });
    } catch (e) {
      setState(() { error = '$e'; loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Search')),
        body: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 8, 18, 12),
            child: Row(children: [
              Expanded(child: TextField(
                controller: q,
                decoration: const InputDecoration(hintText: 'Search your memories…'),
                onSubmitted: (_) => run(),
              )),
              const SizedBox(width: 10),
              FilledButton(onPressed: run, child: const Text('Go')),
            ]),
          ),
          if (loading) const LinearProgressIndicator(),
          if (error != null) Padding(
            padding: const EdgeInsets.all(18),
            child: Text('Search failed: $error'),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 18),
              children: hits.map((h) => MemTile(Map<String, dynamic>.from(h as Map))).toList(),
            ),
          ),
        ]),
      );
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});
  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final q = TextEditingController();
  final log = <Map<String, String>>[
    {'role': 'assistant', 'text': "Hey — I'm your second brain. Ask me anything about your digital life."},
  ];
  final history = <Map<String, String>>[];
  bool busy = false;

  Future<void> send() async {
    final msg = q.text.trim();
    if (msg.isEmpty || busy) return;
    q.clear();
    setState(() {
      log.add({'role': 'user', 'text': msg});
      busy = true;
    });
    history.add({'role': 'user', 'content': msg});
    try {
      final r = await Api.post('/chat', {'message': msg, 'history': history});
      final answer = (r['answer'] ?? '').toString();
      final steps = (r['steps'] as List? ?? [])
          .map((s) => '⚙ ${s['tool']}').join('  ');
      setState(() {
        log.add({'role': 'assistant', 'text': '$answer${steps.isEmpty ? '' : '\n\n$steps'}'});
        busy = false;
      });
      history.add({'role': 'assistant', 'content': answer});
      if (history.length > 40) history.removeRange(0, history.length - 40);
    } catch (e) {
      setState(() {
        log.add({'role': 'assistant', 'text': 'Chat failed: $e'});
        busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Chat')),
      body: Column(children: [
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: log.length,
            itemBuilder: (_, i) {
              final m = log[i];
              final isUser = m['role'] == 'user';
              return Align(
                alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * .82),
                  decoration: BoxDecoration(
                    color: isUser ? cs.primaryContainer : cs.surfaceContainer,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Text(m['text']!, style: TextStyle(
                    color: isUser ? cs.onPrimaryContainer : cs.onSurface,
                    fontSize: 14, height: 1.45)),
                ),
              );
            },
          ),
        ),
        if (busy) const LinearProgressIndicator(),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
            child: Row(children: [
              Expanded(child: TextField(
                controller: q,
                decoration: const InputDecoration(hintText: 'Message your second brain…'),
                onSubmitted: (_) => send(),
              )),
              const SizedBox(width: 10),
              FilledButton(onPressed: send, child: const Icon(Icons.send_rounded)),
            ]),
          ),
        ),
      ]),
    );
  }
}

class SourcesPage extends StatefulWidget {
  const SourcesPage({super.key});
  @override
  State<SourcesPage> createState() => _SourcesPageState();
}

class _SourcesPageState extends State<SourcesPage> {
  List<dynamic> sources = [];
  String? error;

  @override
  void initState() { super.initState(); load(); }

  Future<void> load() async {
    try {
      final r = await Api.get('/sources');
      setState(() { sources = r; error = null; });
    } catch (e) { setState(() { error = '$e'; }); }
  }

  Future<void> sync(String id, Map<String, dynamic> options, int index) async {
    ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Syncing $id…')));
    try {
      final r = await Api.post('/sync', {'source': id, 'options': options});
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('✓ $id: ${r['synced']} documents')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('sync failed: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Sources')),
        body: RefreshIndicator(
          onRefresh: load,
          child: ListView(
            padding: const EdgeInsets.all(18),
            children: [
              if (error != null) Card(child: Padding(
                padding: const EdgeInsets.all(16), child: Text('Offline: $error'))),
              ...sources.asMap().entries.map((e) {
                final s = Map<String, dynamic>.from(e.value as Map);
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Expanded(child: Text(s['label'],
                            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
                        FilledButton.tonal(
                          onPressed: () => sync(s['id'], Map<String, dynamic>.from(s['options'] ?? {}), e.key),
                          child: const Text('Sync'),
                        ),
                      ]),
                      const SizedBox(height: 6),
                      Text(s['description'], style: TextStyle(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                        fontSize: 13),
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 13)),
                      const SizedBox(height: 4),
                      Text('${s['id']} · ${s['requires_google_auth'] == true ? 'google auth' : 'local'}',
                          style: TextStyle(fontSize: 11,
                              color: Theme.of(context).colorScheme.outline)),
                    ]),
                  ),
                );
              }),
            ],
          ),
        ),
      );
}

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});
  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late final TextEditingController base =
      TextEditingController(text: Api.base);
  String status = '';

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(padding: const EdgeInsets.all(18), children: [
        Card(child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('DREAMCORE API', style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1,
              color: cs.onSurfaceVariant)),
            const SizedBox(height: 10),
            TextField(controller: base, decoration: const InputDecoration(
              hintText: 'http://127.0.0.1:8765')),
            const SizedBox(height: 12),
            Row(children: [
              FilledButton.tonal(
                onPressed: () async {
                  Api.base = base.text.trim();
                  setState(() => status = 'checking…');
                  try {
                    await Api.get('/health');
                    setState(() => status = 'connected ✓');
                  } catch (e) { setState(() => status = 'unreachable — $e'); }
                },
                child: const Text('Save & reconnect')),
              const SizedBox(width: 12),
              Text(status, style: TextStyle(color: cs.onSurfaceVariant, fontSize: 13)),
            ]),
          ]),
        )),
        const SizedBox(height: 14),
        Card(child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('LLM PROVIDER', style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1,
              color: cs.onSurfaceVariant)),
            const SizedBox(height: 10),
            Text('Configured on the backend — paste your API key in the web dashboard Setup page or run:\n\ndream config --provider openai-compatible --base-url … --api-key … --model …',
                style: TextStyle(color: cs.onSurfaceVariant, fontSize: 13, height: 1.5)),
          ]),
        )),
        const SizedBox(height: 14),
        Card(child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('PRIVACY', style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1,
              color: cs.onSurfaceVariant)),
            const SizedBox(height: 10),
            Text('• All memories AES-256-GCM encrypted at rest\n• Zero telemetry\n• Requests go only to your API base URL',
                style: TextStyle(color: cs.onSurfaceVariant, fontSize: 13, height: 1.6)),
          ]),
        )),
      ]),
    );
  }
}

// ---------- shell ----------
class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int index = 0;
  bool live = false;

  @override
  void initState() {
    super.initState();
    Api.get('/health').then((_) => setState(() => live = true)).catchError((_) {});
  }

  @override
  Widget build(BuildContext context) {
    final pages = const [
      DashboardPage(), SearchPage(), ChatPage(), SourcesPage(), SettingsPage(),
    ];
    return Scaffold(
      body: IndexedStack(index: index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => setState(() => index = i),
        destinations: [
          const NavigationDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: 'Home'),
          const NavigationDestination(icon: Icon(Icons.search), label: 'Search'),
          const NavigationDestination(icon: Icon(Icons.chat_bubble_outline), selectedIcon: Icon(Icons.chat_bubble), label: 'Chat'),
          const NavigationDestination(icon: Icon(Icons.hub_outlined), selectedIcon: Icon(Icons.hub), label: 'Sources'),
          const NavigationDestination(icon: Icon(Icons.settings_outlined), selectedIcon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
      floatingActionButton: live
          ? FloatingActionButton.small(
              onPressed: () {},
              tooltip: 'Backend connected',
              child: const Icon(Icons.cloud_done, size: 18),
            )
          : null,
    );
  }
}
