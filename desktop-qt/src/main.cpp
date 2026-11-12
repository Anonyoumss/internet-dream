// Internet's Dream — Qt6 desktop client (Material 3 Expressive)
// Thin shell over `dream serve` — every feature lives in the backend.

#include <QApplication>
#include <QMainWindow>
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QListWidget>
#include <QStackedWidget>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QTextBrowser>
#include <QTextEdit>
#include <QScrollArea>
#include <QFrame>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonValue>
#include <QDesktopServices>
#include <QFile>
#include <QStatusBar>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>
#include <QSettings>
#include <QTimer>
#include <QDateTime>
#include <QRegularExpression>
#include <functional>

using JsonCb = std::function<void(bool ok, const QJsonDocument &doc, const QString &err)>;

class Api : public QObject {
    Q_OBJECT
public:
    QNetworkAccessManager nam;
    QString base = QStringLiteral("http://127.0.0.1:8765");

    void get(const QString &path, JsonCb cb) { send("GET", path, {}, cb); }
    void post(const QString &path, const QJsonObject &body, JsonCb cb) {
        send("POST", path, body, cb);
    }

private:
    void send(const QString &method, const QString &path,
              const QJsonObject &body, JsonCb cb) {
        QUrl url(base + path);
        QNetworkRequest req(url);
        req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
        QNetworkReply *r;
        if (method == "GET")
            r = nam.get(req);
        else
            r = nam.post(req, QJsonDocument(body).toJson(QJsonDocument::Compact));
        connect(r, &QNetworkReply::finished, this, [r, cb]() {
            QString err;
            QJsonDocument doc;
            if (r->error() != QNetworkReply::NoError) {
                err = r->errorString();
            } else {
                doc = QJsonDocument::fromJson(r->readAll());
            }
            r->deleteLater();
            cb(err.isEmpty(), doc, err);
        });
    }
};

// ---------- helpers ----------
static QLabel *title(const QString &t) {
    auto *l = new QLabel(t);
    l->setObjectName("pageTitle");
    return l;
}
static QLabel *sub(const QString &t) {
    auto *l = new QLabel(t);
    l->setObjectName("pageSub");
    l->setWordWrap(true);
    return l;
}
static QFrame *card() {
    auto *f = new QFrame;
    f->setObjectName("card");
    return f;
}

// ---------- Dashboard ----------
class DashboardPage : public QWidget {
public:
    Api *api;
    QBoxLayout *statsRow;
    QListWidget *recent;

    DashboardPage(Api *a) : api(a) {
        auto *lay = new QVBoxLayout(this);
        lay->setContentsMargins(28, 24, 28, 24);
        lay->setSpacing(18);
        lay->addWidget(title("Dashboard"));
        lay->addWidget(sub("Your digital life, indexed locally — encrypted at rest."));

        auto *grid = new QHBoxLayout;
        grid->setSpacing(14);
        statsRow = grid;
        lay->addLayout(grid);

        auto *rc = card();
        auto *rl = new QVBoxLayout(rc);
        auto *rt = new QLabel("RECENT MEMORIES"); rt->setObjectName("cardTitle");
        rl->addWidget(rt);
        recent = new QListWidget;
        recent->setMaximumHeight(320);
        rl->addWidget(recent);
        lay->addWidget(rc);
        refresh();
    }

    void refresh() {
        // clear old cards except keep layout
        while (statsRow->count()) {
            auto *it = statsRow->takeAt(0);
            if (it->widget()) it->widget()->deleteLater();
            delete it;
        }
        api->get("/stats", [this](bool ok, const QJsonDocument &d, const QString &) {
            if (!ok) {
                auto *c = card(); auto *l = new QVBoxLayout(c);
                l->addWidget(sub("Offline — start `dream serve` first."));
                statsRow->addWidget(c); return;
            }
            QJsonObject o = d.object();
            int total = o["total"].toInt();
            auto *tc = card(); auto *tl = new QVBoxLayout(tc);
            auto *tt = new QLabel("MEMORIES"); tt->setObjectName("cardTitle");
            auto *ts = new QLabel(QString::number(total)); ts->setObjectName("stat");
            auto *ts2 = new QLabel("encrypted · AES-256-GCM"); ts2->setObjectName("statSub");
            tl->addWidget(tt); tl->addWidget(ts); tl->addWidget(ts2);
            statsRow->addWidget(tc);
            QJsonObject bs = o["by_source"].toObject();
            int shown = 0;
            for (auto it = bs.begin(); it != bs.end() && shown < 4; ++it, ++shown) {
                auto *c = card(); auto *l = new QVBoxLayout(c);
                auto *t2 = new QLabel(it.key().toUpper()); t2->setObjectName("cardTitle");
                auto *s2 = new QLabel(it.value().toString()); s2->setObjectName("stat");
                auto *s3 = new QLabel("indexed documents"); s3->setObjectName("statSub");
                l->addWidget(t2); l->addWidget(s2); l->addWidget(s3);
                statsRow->addWidget(c);
            }
        });
        api->get("/search?q=the&limit=5", [this](bool ok, const QJsonDocument &d, const QString &) {
            recent->clear();
            if (!ok) return;
            for (const auto &v : d.array()) {
                QJsonObject h = v.toObject();
                auto *item = new QListWidgetItem(
                    QString("%1 — %2\n%3")
                        .arg(h["title"].toString(),
                             h["sender"].toString().isEmpty() ? h["source"].toString() : h["sender"].toString(),
                             h["snippet"].toString().left(140)));
                recent->addItem(item);
            }
        });
    }
};

// ---------- Search ----------
class SearchPage : public QWidget {
public:
    Api *api;
    QLineEdit *q;
    QListWidget *results;

    SearchPage(Api *a) : api(a) {
        auto *lay = new QVBoxLayout(this);
        lay->setContentsMargins(28, 24, 28, 24);
        lay->setSpacing(16);
        lay->addWidget(title("Search memories"));
        lay->addWidget(sub("Hybrid keyword + semantic search across everything indexed."));
        auto *box = new QHBoxLayout;
        q = new QLineEdit;
        q->setPlaceholderText("e.g. restaurant recommendation last month…");
        auto *btn = new QPushButton("Search");
        box->addWidget(q); box->addWidget(btn);
        lay->addLayout(box);
        results = new QListWidget;
        lay->addWidget(results, 1);
        connect(btn, &QPushButton::clicked, this, &SearchPage::run);
        connect(q, &QLineEdit::returnPressed, this, &SearchPage::run);
    }
    void run() {
        QString query = q->text().trimmed();
        if (query.isEmpty()) return;
        results->clear();
        api->get("/search?q=" + QUrl::toPercentEncoding(query) + "&limit=20",
                 [this](bool ok, const QJsonDocument &d, const QString &err) {
            if (!ok) {
                results->addItem(new QListWidgetItem("Search failed: " + err));
                return;
            }
            for (const auto &v : d.array()) {
                QJsonObject h = v.toObject();
                results->addItem(new QListWidgetItem(
                    QString("%1\n%2 — %3").arg(h["title"].toString(),
                        h["sender"].toString().isEmpty() ? h["source"].toString() : h["sender"].toString(),
                        h["snippet"].toString().left(200))));
            }
            if (results->count() == 0)
                results->addItem(new QListWidgetItem("No memories matched."));
        });
    }
};

// ---------- Chat (agent) ----------
class ChatPage : public QWidget {
public:
    Api *api;
    QTextBrowser *log;
    QLineEdit *input;
    QJsonArray history;

    ChatPage(Api *a) : api(a) {
        auto *lay = new QVBoxLayout(this);
        lay->setContentsMargins(28, 24, 28, 24);
        lay->setSpacing(14);
        lay->addWidget(title("Chat"));
        lay->addWidget(sub("Your AI agent — it can search memory, sync sources, and save notes."));
        log = new QTextBrowser;
        log->setObjectName("chatLog");
        lay->addWidget(log, 1);
        auto *box = new QHBoxLayout;
        input = new QLineEdit;
        input->setPlaceholderText("Ask anything about your digital life…");
        auto *btn = new QPushButton("Send");
        box->addWidget(input); box->addWidget(btn);
        lay->addLayout(box);
        connect(btn, &QPushButton::clicked, this, &ChatPage::send);
        connect(input, &QLineEdit::returnPressed, this, &ChatPage::send);
        append("assistant", "Hey — I'm your second brain. Ask me anything, or tell me to sync/import something.");
    }

    void append(const QString &role, const QString &text) {
        QString color = role == "user" ? "#6d4bd8" : "#46415c";
        QString who = role == "user" ? "You" : "Dream";
        log->append(QString("<div style='margin:8px 0'><b style='color:%1'>%2</b><br>%3</div>")
                        .arg(color, who, text.toHtmlEscaped().replace("\n", "<br>")));
    }

    void send() {
        QString msg = input->text().trimmed();
        if (msg.isEmpty()) return;
        input->clear();
        append("user", msg);
        history.append(QJsonObject{{"role", "user"}, {"content", msg}});
        QJsonObject body{{"message", msg}, {"history", history}};
        api->post("/chat", body, [this, msg](bool ok, const QJsonDocument &d, const QString &err) {
            if (!ok) { append("assistant", "Chat failed: " + err); return; }
            QJsonObject o = d.object();
            QString answer = o["answer"].toString();
            QString extra;
            for (const auto &v : o["steps"].toArray()) {
                QJsonObject s = v.toObject();
                extra += QString("<br><i>⚙ %1(%2)</i>")
                    .arg(s["tool"].toString(),
                         QString::fromUtf8(QJsonDocument(s["args"].toObject()).toJson(QJsonDocument::Compact)).left(90));
            }
            append("assistant", answer + extra);
            history.append(QJsonObject{{"role", "assistant"}, {"content", answer}});
            if (history.size() > 40) {
                QJsonArray trimmed;
                for (int i = history.size() - 40; i < history.size(); ++i)
                    trimmed.append(history[i]);
                history = trimmed;
            }
        });
    }
};

// ---------- Sources ----------
class SourcesPage : public QWidget {
public:
    Api *api;
    QVBoxLayout *list;

    SourcesPage(Api *a) : api(a) {
        auto *lay = new QVBoxLayout(this);
        lay->setContentsMargins(28, 24, 28, 24);
        lay->setSpacing(16);
        lay->addWidget(title("Sources"));
        lay->addWidget(sub("Connect your apps. Google sources need a one-time OAuth consent; Discord/Telegram/WhatsApp use local credentials."));
        auto *scroll = new QScrollArea;
        scroll->setWidgetResizable(true);
        auto *inner = new QWidget;
        list = new QVBoxLayout(inner);
        list->setSpacing(12);
        list->addStretch();
        scroll->setWidget(inner);
        lay->addWidget(scroll, 1);
        refresh();
    }

    void refresh() {
        // remove old cards
        while (list->count() > 1) {
            auto *it = list->takeAt(0);
            if (it->widget()) it->widget()->deleteLater();
            delete it;
        }
        api->get("/sources", [this](bool ok, const QJsonDocument &d, const QString &err) {
            if (!ok) {
                auto *c = card(); auto *l = new QVBoxLayout(c);
                l->addWidget(sub("Offline — " + err));
                list->insertWidget(0, c); return;
            }
            QJsonArray arr = d.array();
            for (int i = arr.size() - 1; i >= 0; --i) {
                list->insertWidget(list->count() - 1, makeCard(arr[i].toObject()));
            }
        });
    }

    QWidget *makeCard(const QJsonObject &s) {
        QString id = s["id"].toString();
        auto *c = card();
        auto *l = new QVBoxLayout(c);
        auto *head = new QHBoxLayout;
        auto *name = new QLabel(s["label"].toString());
        name->setStyleSheet("font-weight:700;font-size:15px");
        auto *btn = new QPushButton("Sync");
        btn->setObjectName("tonal");
        head->addWidget(name); head->addStretch(); head->addWidget(btn);
        auto *desc = new QLabel(s["description"].toString());
        desc->setObjectName("pageSub"); desc->setWordWrap(true);
        auto *opts = new QLineEdit(
            QString::fromUtf8(QJsonDocument(s["options"].toObject()).toJson(QJsonDocument::Compact)));
        opts->setPlaceholderText("options JSON");
        auto *status = new QLabel;
        status->setObjectName("pageSub");
        l->addLayout(head); l->addWidget(desc); l->addWidget(opts); l->addWidget(status);
        connect(btn, &QPushButton::clicked, this, [this, id, opts, status, btn]() {
            QJsonParseError pe{};
            QJsonDocument od = QJsonDocument::fromJson(opts->text().toUtf8(), &pe);
            QJsonObject options = pe.error == QJsonParseError::NoError ? od.object() : QJsonObject{};
            btn->setEnabled(false); status->setText("syncing…");
            api->post("/sync", QJsonObject{{"source", id}, {"options", options}},
                      [status, btn, this](bool ok, const QJsonDocument &d, const QString &err) {
                btn->setEnabled(true);
                if (ok) status->setText(QString("✓ synced %1 documents").arg(d.object()["synced"].toInt()));
                else status->setText("sync failed: " + err);
            });
        });
        return c;
    }
};

// ---------- Settings ----------
class SettingsPage : public QWidget {
public:
    Api *api;
    QLineEdit *baseEdit;
    QLabel *status;

    SettingsPage(Api *a, const QString &saved) : api(a) {
        auto *lay = new QVBoxLayout(this);
        lay->setContentsMargins(28, 24, 28, 24);
        lay->setSpacing(18);
        lay->addWidget(title("Settings"));
        lay->addWidget(sub("Connection and privacy. Keys live in ~/.internet-dream — never sent anywhere but your configured endpoints."));

        auto *c = card(); auto *l = new QVBoxLayout(c);
        auto *t = new QLabel("dreamcore API"); t->setObjectName("cardTitle");
        l->addWidget(t);
        baseEdit = new QLineEdit(saved);
        baseEdit->setPlaceholderText("http://127.0.0.1:8765");
        l->addWidget(baseEdit);
        auto *row = new QHBoxLayout;
        auto *save = new QPushButton("Save & reconnect");
        save->setObjectName("tonal");
        status = new QLabel; status->setObjectName("pageSub");
        row->addWidget(save); row->addWidget(status); row->addStretch();
        l->addLayout(row);
        lay->addWidget(c);

        auto *g = card(); auto *gl = new QVBoxLayout(g);
        auto *gt = new QLabel("GOOGLE ACCOUNT"); gt->setObjectName("cardTitle");
        gl->addWidget(gt);
        auto *gs = new QLabel("One backend consent unlocks Gmail, Calendar, Drive, Photos for every client.\nRequires ~/.internet-dream/client_secret.json");
        gs->setObjectName("pageSub"); gs->setWordWrap(true);
        gl->addWidget(gs);
        auto *btn = new QPushButton("Connect Google account");
        connect(btn, &QPushButton::clicked, this, [this]() {
            QDesktopServices::openUrl(QUrl(api->base + "/auth/google/start"));
        });
        gl->addWidget(btn, 0, Qt::AlignLeft);
        lay->addWidget(g);
        lay->addStretch();

        connect(save, &QPushButton::clicked, this, [this]() {
            api->base = baseEdit->text().trimmed();
            QSettings().setValue("apiBase", api->base);
            status->setText("checking…");
            api->get("/health", [this](bool ok, const QJsonDocument &, const QString &err) {
                status->setText(ok ? "connected ✓" : "unreachable — " + err);
            });
        });
    }
};

// ---------- Main window ----------
class MainWindow : public QMainWindow {
public:
    Api api;
    QStackedWidget *stack;
    QListWidget *rail;
    DashboardPage *dash;

    MainWindow() {
        setWindowTitle("Internet's Dream");
        resize(1100, 720);

        QSettings s;
        api.base = s.value("apiBase", "http://127.0.0.1:8765").toString();

        auto *central = new QWidget;
        auto *root = new QHBoxLayout(central);
        root->setContentsMargins(0, 0, 0, 0);
        root->setSpacing(0);

        rail = new QListWidget;
        rail->setObjectName("rail");
        rail->setFixedWidth(110);
        rail->setIconSize(QSize(0, 0));
        QStringList items = {"Dashboard", "Search", "Chat", "Sources", "Settings"};
        for (const auto &i : items) rail->addItem(i);

        stack = new QStackedWidget;
        dash = new DashboardPage(&api);
        stack->addWidget(dash);
        stack->addWidget(new SearchPage(&api));
        stack->addWidget(new ChatPage(&api));
        stack->addWidget(new SourcesPage(&api));
        stack->addWidget(new SettingsPage(&api, api.base));

        root->addWidget(rail);
        root->addWidget(stack, 1);
        setCentralWidget(central);

        connect(rail, &QListWidget::currentRowChanged, stack, &QStackedWidget::setCurrentIndex);
        rail->setCurrentRow(0);

        // connectivity chip in window title bar area
        auto *chip = new QLabel("checking…");
        chip->setObjectName("chip");
        statusBar()->addPermanentWidget(chip);
        api.get("/health", [chip](bool ok, const QJsonDocument &d, const QString &) {
            if (ok) {
                chip->setObjectName("chipLive");
                chip->setText(QString("live · %1 memories").arg(d.object()["docs"].toInt()));
            } else {
                chip->setText("offline — start `dream serve`");
            }
            chip->style()->unpolish(chip); chip->style()->polish(chip);
        });

        // refresh dashboard when returning to it
        connect(rail, &QListWidget::currentRowChanged, this, [this](int row) {
            if (row == 0) dash->refresh();
        });
    }
};

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    app.setApplicationName("Internet's Dream");
    app.setOrganizationName("internet-dream");

    // --smoke: hit /health and exit (for CI/headless tests)
    for (int i = 1; i < argc; ++i) {
        if (QString(argv[i]) == "--smoke") {
            Api api;
            QEventLoop loop;
            bool ok = false;
            api.get("/health", [&](bool o, const QJsonDocument &d, const QString &) {
                ok = o && d.object()["ok"].toBool();
                loop.quit();
            });
            QTimer::singleShot(8000, &loop, &QEventLoop::quit);
            loop.exec();
            return ok ? 0 : 2;
        }
    }

    QFile qss(":/theme.qss");
    if (!qss.open(QIODevice::ReadOnly)) {
        // fallback: load from filesystem next to binary / repo
        for (const QString &p : {QStringLiteral("resources/theme.qss"),
                                  QStringLiteral("../resources/theme.qss")}) {
            QFile f(p);
            if (f.open(QIODevice::ReadOnly)) { app.setStyleSheet(QString::fromUtf8(f.readAll())); break; }
        }
    } else {
        app.setStyleSheet(QString::fromUtf8(qss.readAll()));
    }

    MainWindow w;
    w.show();
    return app.exec();
}

#include "main.moc"
