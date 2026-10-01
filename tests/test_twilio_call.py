"""Offline tests for bin/twilio-call. Run: python3 -m unittest discover tests

A stateful fake stands in for the Twilio REST API, so no credentials are
needed and no calls are placed.
"""
import base64
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "bin", "twilio-call")

loader = SourceFileLoader("twilio_call", SCRIPT)
tc = module_from_spec(spec_from_loader("twilio_call", loader))
loader.exec_module(tc)

ACCOUNT = "AC" + "0" * 32
CALL = "CA" + "1" * 32
ENV = {"TWILIO_ACCOUNT_SID": ACCOUNT, "TWILIO_AUTH_TOKEN": "test-token"}


class FakeTwilio:
    """Minimal in-memory model of the endpoints the CLI uses."""

    def __init__(self):
        self.services, self.sync_services, self.envs = [], [], []
        self.functions, self.variables, self.maps = [], [], []
        self.map_items, self.calls, self.log = {}, [], []
        self.numbers = [{"phone_number": "+15550000001", "capabilities": {"voice": True}}]
        self.n = 0

    def sid(self, prefix):
        self.n += 1
        return f"{prefix}{self.n:032x}"

    def __call__(self, method, url, form=None, multipart=None, ok404=False):
        self.log.append((method, url, form, multipart))
        path = urllib.parse.urlparse(url).path
        host = urllib.parse.urlparse(url).netloc
        if host == "serverless.twilio.com":
            return self.serverless(method, path, form)
        if host == "serverless-upload.twilio.com":
            return {"sid": self.sid("ZN")}
        if host == "sync.twilio.com":
            return self.sync(method, path, form, ok404)
        if host == "api.twilio.com":
            return self.api(method, path, form)
        raise AssertionError(f"unexpected {method} {url}")

    def serverless(self, method, path, form):
        if path == "/v1/Services":
            if method == "GET":
                return {"services": self.services}
            s = {"sid": self.sid("ZS"), "unique_name": form["UniqueName"],
                 "include_credentials": form["IncludeCredentials"] == "true"}
            self.services.append(s)
            return s
        if path.endswith("/Environments"):
            if method == "GET":
                return {"environments": self.envs}
            e = {"sid": self.sid("ZE"), "unique_name": form["UniqueName"],
                 "domain_name": "muse-phone-calls-1234-prod.twil.io"}
            self.envs.append(e)
            return e
        if re.search(r"/Environments/ZE\w+$", path):
            return self.envs[0]
        if path.endswith("/Functions"):
            if method == "GET":
                return {"functions": self.functions}
            f = {"sid": self.sid("ZH"), "friendly_name": form["FriendlyName"]}
            self.functions.append(f)
            return f
        if path.endswith("/Variables"):
            if method == "GET":
                return {"variables": self.variables}
            v = {"sid": self.sid("ZV"), "key": form["Key"], "value": form["Value"]}
            self.variables.append(v)
            return v
        m = re.search(r"/Variables/(ZV\w+)$", path)
        if m:
            v = next(v for v in self.variables if v["sid"] == m.group(1))
            v["value"] = form["Value"]
            return v
        if path.endswith("/Builds"):
            self.build = {"sid": self.sid("ZB"), "status": "building", "form": form}
            return dict(self.build)
        if "/Builds/" in path:
            self.build["status"] = "completed"
            return dict(self.build)
        if path.endswith("/Deployments"):
            return {"sid": self.sid("ZD"), "build_sid": form["BuildSid"]}
        raise AssertionError(f"unexpected serverless {method} {path}")

    def sync(self, method, path, form, ok404):
        if path == "/v1/Services":
            if method == "GET":
                return {"services": self.sync_services}
            s = {"sid": self.sid("IS"), "unique_name": form["UniqueName"]}
            self.sync_services.append(s)
            return s
        if path.endswith("/Maps"):
            self.maps.append(form["UniqueName"])
            return {"sid": self.sid("MP")}
        m = re.search(r"/Maps/([\w-]+)$", path)
        if m:
            return {"unique_name": m.group(1)} if m.group(1) in self.maps else None
        m = re.search(r"/Items/(\w+)$", path)
        if m:
            item = self.map_items.get(m.group(1))
            return {"key": m.group(1), "data": item} if item else None
        raise AssertionError(f"unexpected sync {method} {path}")

    def api(self, method, path, form):
        if path.endswith("/IncomingPhoneNumbers.json"):
            return {"incoming_phone_numbers": self.numbers}
        if path.endswith("/Calls.json"):
            self.calls.append(form)
            return {"sid": CALL, "status": "queued", "to": form["To"], "from": form["From"]}
        if path.endswith(f"/Calls/{CALL}.json"):
            return {"sid": CALL, "status": "completed", "duration": "12",
                    "start_time": "s", "end_time": "e", "date_created": "c",
                    "date_updated": "u", "price": "-0.014"}
        raise AssertionError(f"unexpected api {method} {path}")


class CLITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = os.path.join(self.tmp, "config.json")
        self.fake = FakeTwilio()
        for p in (
            mock.patch.object(tc, "CONFIG_PATH", self.cfg),
            mock.patch.object(tc, "request", self.fake),
            mock.patch.object(tc.time, "sleep", lambda s: None),
            mock.patch.dict(os.environ, ENV),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with mock.patch.object(sys, "argv", ["twilio-call", *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                tc.main()
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def setup_ok(self, *extra):
        code, out, err = self.run_cli("setup", *extra)
        self.assertEqual(code, 0, err)
        with open(self.cfg) as f:
            return json.load(f)

    # setup -----------------------------------------------------------
    def test_setup_provisions_everything_and_writes_config(self):
        cfg = self.setup_ok()
        self.assertEqual(cfg["from_number"], "+15550000001")
        self.assertEqual(cfg["domain"], "muse-phone-calls-1234-prod.twil.io")
        self.assertEqual(cfg["map_name"], "keypad-results")
        self.assertTrue(self.fake.services[0]["include_credentials"])
        self.assertEqual({v["key"]: v["value"] for v in self.fake.variables},
                         {"SYNC_SERVICE_SID": cfg["sync_service_sid"],
                          "SYNC_MAP_NAME": "keypad-results"})
        upload = next(m for _, u, _, m in self.fake.log if "serverless-upload" in u)
        self.assertEqual(upload["Path"], "/gather-handler")
        self.assertEqual(upload["Visibility"], "protected")
        deps = json.loads(self.fake.build["form"]["Dependencies"])
        self.assertIn("twilio", [d["name"] for d in deps])
        self.assertEqual(os.stat(self.cfg).st_mode & 0o777, 0o600)

    def test_config_never_contains_credentials(self):
        self.setup_ok()
        with open(self.cfg) as f:
            raw = f.read()
        self.assertNotIn("test-token", raw)
        self.assertNotIn(ACCOUNT, raw)

    def test_setup_is_idempotent(self):
        self.setup_ok()
        self.setup_ok()
        f = self.fake
        self.assertEqual((len(f.services), len(f.sync_services), len(f.envs),
                          len(f.functions), len(f.variables), len(f.maps)),
                         (1, 1, 1, 1, 2, 1))

    def test_setup_from_flag(self):
        self.assertEqual(self.setup_ok("--from", "+15559990000")["from_number"], "+15559990000")

    def test_setup_without_voice_number_fails(self):
        self.fake.numbers = []
        code, _, err = self.run_cli("setup")
        self.assertEqual(code, 1)
        self.assertIn("No voice-capable", err)

    # place -----------------------------------------------------------
    def test_place_plain_message(self):
        self.setup_ok()
        code, out, err = self.run_cli("place", "--to", "+15551234567", "--message", "Hi & bye")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["sid"], CALL)
        call = self.fake.calls[0]
        self.assertEqual(call["From"], "+15550000001")
        self.assertEqual(call["Twiml"], "<Response><Say>Hi &amp; bye</Say></Response>")

    def test_place_with_menu_points_gather_at_function(self):
        self.setup_ok()
        self.run_cli("place", "--to", "+15551234567", "--message", "Confirm?",
                     "--menu", "1:Confirm,2:Cancel")
        twiml = self.fake.calls[0]["Twiml"]
        self.assertIn('numDigits="1"', twiml)
        self.assertIn('action="https://muse-phone-calls-1234-prod.twil.io/gather-handler"', twiml)
        self.assertIn("Press 1 to Confirm. Press 2 to Cancel.", twiml)

    def test_place_from_override(self):
        self.setup_ok()
        self.run_cli("place", "--to", "+15551234567", "--message", "x", "--from", "+15557654321")
        self.assertEqual(self.fake.calls[0]["From"], "+15557654321")

    def test_dry_run_places_no_call_and_needs_no_credentials(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            code, out, _ = self.run_cli("place", "--to", "+15551234567",
                                        "--message", "Hello.", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "<Response><Say>Hello.</Say></Response>")
        self.assertEqual(self.fake.calls, [])

    def test_menu_without_setup_fails(self):
        code, _, err = self.run_cli("place", "--to", "+15551234567", "--message", "x",
                                    "--menu", "1:Yes")
        self.assertEqual(code, 1)
        self.assertIn("setup", err)

    def test_invalid_inputs_rejected(self):
        self.setup_ok()
        for argv in (
            ("place", "--to", "5551234567", "--message", "x"),
            ("place", "--to", "+15551234567", "--message", "x", "--from", "bad"),
            ("place", "--to", "+15551234567", "--message", "x", "--menu", "10:Ten"),
            ("place", "--to", "+15551234567", "--message", "x", "--menu", "1"),
            ("status", "--sid", "not-a-sid"),
            ("result", "--sid", "CA123"),
        ):
            code, _, _ = self.run_cli(*argv)
            self.assertEqual(code, 1, argv)
        self.assertEqual(self.fake.calls, [])

    # status / result ---------------------------------------------------
    def test_status(self):
        code, out, _ = self.run_cli("status", "--sid", CALL)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "completed")
        self.assertEqual(json.loads(out)["duration"], "12")

    def test_result_returns_captured_digit(self):
        self.setup_ok()
        self.fake.map_items[CALL] = {"digits": "1"}
        _, out, _ = self.run_cli("result", "--sid", CALL)
        self.assertEqual(json.loads(out), {"sid": CALL, "digits": "1"})

    def test_result_null_when_nothing_captured(self):
        self.setup_ok()
        _, out, _ = self.run_cli("result", "--sid", CALL, "--wait", "1")
        self.assertEqual(json.loads(out), {"sid": CALL, "digits": None})

    def test_result_wait_picks_up_late_digit(self):
        self.setup_ok()
        real = self.fake.sync
        polls = []

        def sync(method, path, form, ok404):
            polls.append(path)
            if len(polls) == 3:
                self.fake.map_items[CALL] = {"digits": "2"}
            return real(method, path, form, ok404)

        self.fake.sync = sync
        _, out, _ = self.run_cli("result", "--sid", CALL, "--wait", "30")
        self.assertEqual(json.loads(out)["digits"], "2")
        self.assertGreaterEqual(len(polls), 3)


class HTTPLayerTest(unittest.TestCase):
    """Exercise the real request() against a patched urlopen."""

    def setUp(self):
        p = mock.patch.dict(os.environ, ENV)
        p.start()
        self.addCleanup(p.stop)

    def test_basic_auth_and_form_encoding(self):
        seen = {}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        def urlopen(req, timeout):
            seen["req"] = req
            return Resp(b'{"ok": true}')

        with mock.patch.object(tc.urllib.request, "urlopen", urlopen):
            tc.request("POST", "https://api.twilio.com/x", form={"To": "+1", "List": ["a", "b"]})
        req = seen["req"]
        token = base64.b64encode(f"{ACCOUNT}:test-token".encode()).decode()
        self.assertEqual(req.get_header("Authorization"), f"Basic {token}")
        self.assertEqual(req.data, b"To=%2B1&List=a&List=b")

    def test_twilio_error_code_and_message_surface(self):
        body = io.BytesIO(json.dumps(
            {"code": 21211, "message": "The 'To' number is not a valid phone number."}).encode())
        err = urllib.error.HTTPError("u", 400, "Bad Request", {}, body)
        with mock.patch.object(tc.urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(tc.TwilioError) as cm:
                tc.request("POST", "https://api.twilio.com/x", form={})
        self.assertEqual(str(cm.exception),
                         "Twilio error 21211: The 'To' number is not a valid phone number.")

    def test_missing_credentials(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(tc.TwilioError):
                tc.request("GET", "https://api.twilio.com/x")


@unittest.skipUnless(shutil.which("node"), "node not installed")
class FunctionTest(unittest.TestCase):
    """Run the deployed gather-handler JS with a mocked Twilio client."""

    HARNESS = r"""
const code = require('fs').readFileSync(0, 'utf8');
const writes = [];
let existing = process.env.EXISTING === '1';
const items = (key) => ({ update: async (p) => { writes.push({ op: 'update', key, ...p }); } });
items.create = async (p) => {
  if (existing) { const e = new Error('exists'); e.status = 409; throw e; }
  writes.push({ op: 'create', ...p });
};
const client = { sync: { v1: { services: (s) => ({ syncMaps: (m) => ({ syncMapItems: items, s, m }) }) } } };
class VoiceResponse { constructor() { this.v = []; } say(t) { this.v.push('say:' + t); } hangup() { this.v.push('hangup'); } }
global.Twilio = { twiml: { VoiceResponse } };
const exports_ = {};
new Function('exports', code)(exports_);
const ctx = { getTwilioClient: () => client, SYNC_SERVICE_SID: 'IS1', SYNC_MAP_NAME: 'keypad-results' };
exports_.handler(ctx, JSON.parse(process.env.EVENT), (err, twiml) => {
  console.log(JSON.stringify({ err: err ? String(err) : null, writes, twiml: twiml && twiml.v }));
});
"""

    def run_fn(self, event, existing=False):
        env = dict(os.environ, EVENT=json.dumps(event), EXISTING="1" if existing else "0")
        out = subprocess.run(["node", "-e", self.HARNESS], input=tc.FUNCTION_CODE,
                             capture_output=True, text=True, env=env, check=True).stdout
        return json.loads(out)

    def test_records_digit_with_24h_ttl(self):
        r = self.run_fn({"CallSid": CALL, "Digits": "1"})
        self.assertIsNone(r["err"])
        self.assertEqual(r["writes"], [{"op": "create", "key": CALL,
                                        "data": {"digits": "1"}, "ttl": 86400}])
        self.assertEqual(r["twiml"], ["say:Thank you. Goodbye.", "hangup"])

    def test_overwrites_existing_item(self):
        r = self.run_fn({"CallSid": CALL, "Digits": "2"}, existing=True)
        self.assertIsNone(r["err"])
        self.assertEqual(r["writes"][0]["op"], "update")
        self.assertEqual(r["writes"][0]["data"], {"digits": "2"})

    def test_no_digits_records_nothing(self):
        r = self.run_fn({"CallSid": CALL})
        self.assertEqual(r["writes"], [])


if __name__ == "__main__":
    unittest.main()
