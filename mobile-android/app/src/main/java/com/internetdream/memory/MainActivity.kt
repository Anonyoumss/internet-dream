package com.internetdream.memory

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class Hit(
    val title: String,
    val sender: String?,
    val source: String,
    val snippet: String?,
)

class DreamViewModel : ViewModel() {
    var apiBase by mutableStateOf("http://10.0.2.2:8765")
    var online by mutableStateOf(false)
    var total by mutableStateOf(0)
    var bySource by mutableStateOf(mapOf<String, Int>())
    var results by mutableStateOf<List<Hit>>(emptyList())
    var answer by mutableStateOf("")
    var query by mutableStateOf("")

    private fun http(path: String, method: String = "GET", body: String? = null): String {
        val conn = URL(apiBase + path).openConnection() as HttpURLConnection
        conn.requestMethod = method
        conn.connectTimeout = 4000
        conn.readTimeout = 30000
        if (body != null) {
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.outputStream.write(body.toByteArray())
        }
        return conn.inputStream.bufferedReader().readText()
    }

    fun refresh() {
        viewModelScope.launch {
            online = withContext(Dispatchers.IO) {
                try {
                    val stats = JSONObject(http("/stats"))
                    total = stats.optInt("total")
                    val bs = stats.optJSONObject("by_source")
                    bySource = bs?.keys()?.asSequence()
                        ?.associateWith { bs.optInt(it) } ?: emptyMap()
                    true
                } catch (e: Exception) { false }
            }
        }
    }

    fun search() {
        val q = query.trim()
        if (q.isEmpty()) return
        viewModelScope.launch {
            results = withContext(Dispatchers.IO) {
                try {
                    val arr = org.json.JSONArray(
                        http("/search?q=" + URLEncoder.encode(q, "UTF-8") + "&limit=20"))
                    (0 until arr.length()).map {
                        val o = arr.getJSONObject(it)
                        Hit(o.optString("title"), o.optString("sender").ifEmpty { null },
                            o.optString("source"), o.optString("snippet"))
                    }
                } catch (e: Exception) { emptyList() }
            }
        }
    }

    fun ask() {
        val q = query.trim()
        if (q.isEmpty()) return
        answer = "Thinking…"
        viewModelScope.launch {
            answer = withContext(Dispatchers.IO) {
                try {
                    val payload = JSONObject().put("question", q).toString()
                    JSONObject(http("/ask", "POST", payload)).optString("answer")
                } catch (e: Exception) { "backend offline — run `dream serve` on your computer" }
            }
        }
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = lightColorScheme(
                primary = androidx.compose.ui.graphics.Color(0xFF6750A4),
                onPrimary = androidx.compose.ui.graphics.Color.White,
                primaryContainer = androidx.compose.ui.graphics.Color(0xFFEADDFF),
                onPrimaryContainer = androidx.compose.ui.graphics.Color(0xFF21005D),
                surface = androidx.compose.ui.graphics.Color(0xFFFEF7FF),
                onSurface = androidx.compose.ui.graphics.Color(0xFF1D1B20),
                surfaceVariant = androidx.compose.ui.graphics.Color(0xFFE7E0EC),
                onSurfaceVariant = androidx.compose.ui.graphics.Color(0xFF49454F),
            )) {
                DreamApp()
            }
        }
    }
}

@Composable
fun DreamApp(vm: DreamViewModel = viewModel()) {
    var tab by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) { vm.refresh() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Internet's Dream", fontWeight = FontWeight.SemiBold) },
                actions = {
                    Text(if (vm.online) "● live" else "○ demo",
                        style = MaterialTheme.typography.labelMedium,
                        color = if (vm.online) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(end = 16.dp))
                },
            )
        },
        bottomBar = {
            NavigationBar {
                NavigationBarItem(selected = tab == 0, onClick = { tab = 0 },
                    icon = { Icon(Icons.Default.Home, null) }, label = { Text("Home") })
                NavigationBarItem(selected = tab == 1, onClick = { tab = 1 },
                    icon = { Icon(Icons.Default.Search, null) }, label = { Text("Search") })
                NavigationBarItem(selected = tab == 2, onClick = { tab = 2 },
                    icon = { Icon(Icons.Default.Info, null) }, label = { Text("Ask") })
                NavigationBarItem(selected = tab == 3, onClick = { tab = 3 },
                    icon = { Icon(Icons.Default.Settings, null) }, label = { Text("Settings") })
            }
        },
    ) { pad ->
        Box(Modifier.padding(pad).fillMaxSize()) {
            when (tab) {
                0 -> DashboardTab(vm)
                1 -> SearchTab(vm)
                2 -> AskTab(vm)
                else -> SettingsTab(vm)
            }
        }
    }
}

@Composable
fun DashboardTab(vm: DreamViewModel) {
    Column(Modifier.padding(20.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Your digital life, indexed locally.",
            style = MaterialTheme.typography.titleLarge)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Card(Modifier.weight(1f)) {
                Column(Modifier.padding(16.dp)) {
                    Text("Memories", style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("${vm.total}", style = MaterialTheme.typography.displaySmall)
                }
            }
            Card(Modifier.weight(1f)) {
                Column(Modifier.padding(16.dp)) {
                    Text("Backend", style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(if (vm.online) "Connected" else "Offline",
                        style = MaterialTheme.typography.titleLarge,
                        color = if (vm.online) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        Card {
            Text("AES-256-GCM encrypted at rest · zero telemetry · data stays on your devices.",
                Modifier.padding(16.dp), style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        vm.bySource.forEach { (k, v) ->
            ListItem(headlineContent = { Text(k) },
                supportingContent = { Text("$v documents") },
                trailingContent = { Text("", style = MaterialTheme.typography.labelMedium) })
        }
    }
}

@Composable
fun SearchTab(vm: DreamViewModel) {
    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        OutlinedTextField(
            value = vm.query, onValueChange = { vm.query = it },
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("Search your memories…") },
            leadingIcon = { Icon(Icons.Default.Search, null) },
            singleLine = true,
        )
        Button(onClick = { vm.search() }, modifier = Modifier.fillMaxWidth()) { Text("Search") }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(vm.results) { h ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp)) {
                        Text(h.title, fontWeight = FontWeight.SemiBold)
                        Text("${h.sender ?: "unknown"} · ${h.source}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                        h.snippet?.let {
                            Text(it.take(180), style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AskTab(vm: DreamViewModel) {
    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        OutlinedTextField(
            value = vm.query, onValueChange = { vm.query = it },
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("Ask your second brain…") },
            singleLine = true,
        )
        Button(onClick = { vm.ask() }, modifier = Modifier.fillMaxWidth()) { Text("Ask") }
        Card(Modifier.fillMaxWidth()) {
            Text(vm.answer.ifEmpty { "Answers are grounded in your indexed memories and cite sources." },
                Modifier.padding(16.dp), style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
fun SettingsTab(vm: DreamViewModel) {
    Column(Modifier.padding(20.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Settings", style = MaterialTheme.typography.titleLarge)
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("dreamcore API", fontWeight = FontWeight.SemiBold)
                Text("Default on emulator: http://10.0.2.2:8765 (host loopback). " +
                     "On a real device use your computer's LAN IP.")
                OutlinedTextField(value = vm.apiBase, onValueChange = { vm.apiBase = it },
                    modifier = Modifier.fillMaxWidth(), label = { Text("API base URL") })
                Button(onClick = { vm.refresh() }) { Text("Reconnect") }
            }
        }
        Card {
            Text("Configure the LLM gateway on the backend:\n\n" +
                 "  dream config --provider openai-compatible \\\n" +
                 "    --base-url https://api.openai.com/v1 \\\n" +
                 "    --api-key sk-... --model gpt-4o-mini",
                Modifier.padding(16.dp), style = MaterialTheme.typography.bodySmall)
        }
    }
}
