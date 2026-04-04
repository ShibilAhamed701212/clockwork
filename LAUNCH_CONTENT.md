# Demo Scripts

---

## 1. GIF Demo Script (30 seconds)

### Scene 1: Failure (5s)
```
Terminal shows:
$ clockwork ci-run
▶ Stage 1: build ✓
▶ Stage 2: test ✗ FAIL: test_user.py::test_login_invalid
   → Retry 1/3... ✗
   → Retry 2/3... ✗
```

### Scene 2: AI Analysis (5s)
```
   → AI analyzing error...
   → "Password validation regex too strict.
       Should accept special chars."
```

### Scene 3: User Decision (5s)
```
   ? Apply fix? (y/N): y
   ✓ Fix applied
   → Retrying tests...
```

### Scene 4: Success (5s)
```
   ✓ All 23 tests passed
▶ Stage 3: deploy → skipped

✓ Pipeline passed (1 fix applied)
```

### Scene 5: Branding (5s)
```
Clockwork
Self-healing CI/CD
pip install clockwork
```

---

## 2. 60-Second Video Script

### 0-5s: HOOK
```
[Screen: Developer asleep, phone buzzes with CI failure]

Narrator: "It's 2am. Your CI failed again."

[Phone shows: "test_api.py FAILED"]
```

### 5-15s: PROBLEM
```
[Screen: Developer sighs, opens laptop]

Narrator: "You wake up, check the error, fix it, push again.
This happens way too often."
```

### 15-30s: SOLUTION
```
[Screen: Clockwork running]

Narrator: "What if your pipeline fixed itself?"

[Show: clockwork ci-run with auto-retry]
```

### 30-50s: DEMO
```
[Full demo of failure → retry → AI → fix → pass]

Narrator: "Clockwork runs your pipeline. Retries on failure.
If enabled, AI analyzes the error, suggests a fix.
You approve. Pipeline passes. You sleep."
```

### 50-60s: CTA
```
[Screen: pip install clockwork]

Narrator: "pip install clockwork
It works without AI. AI helps when you want it."

[Show GitHub link]
```

---

## Reddit Post

---

**Title:** I built a CI/CD that fixes itself when tests fail (works without AI)

**Body:**

So I'm tired of waking up to CI failures for dumb reasons.

Most CI tools:
- Make you wait 20 minutes to tell you a test failed
- Don't retry automatically
- Need a PhD to configure their YAML

I wanted something simple:
- Runs locally
- Retries when things break
- Actually understandable

So I built **Clockwork**.

```
$ clockwork ci-run

▶ Stage 1: build ✓
▶ Stage 2: test ✗ FAIL

   → Retry 1/3... ✗ still failing
   
   → AI: "Add null check on line 42"
   ? Apply fix? (y/N): y
   
   → Retrying tests...
   ✓ All tests passed
```

**Key features:**
- Auto-retries on failure (up to 3x)
- Optional AI that suggests fixes (you approve everything)
- Runs locally (no cloud waiting)
- Works perfectly without AI
- Simple YAML config

No I'm not trying to replace GitHub Actions. It's for:
- Side projects
- Solo developers
- Local dev loops

Link: [GitHub - ShibilAhamed701212/clockwork](https://github.com/ShibilAhamed701212/clockwork)

Curious what people think. Too niche? Would love feedback.

---

## Twitter/X Thread

---

**Tweet 1 (Hook):**
```
Woke up to another CI failure at 2am.

Built a tool that fixes itself instead.

🧵
```

**Tweet 2 (Problem):**
```
Traditional CI:
1. Push code
2. Wait 20 min
3. CI fails on a semicolon
4. Wake up anyway
5. Fix, push, wait again

Rinse. Repeat.
```

**Tweet 3 (What it does):**
```
Clockwork:

→ Runs your pipeline (local or CI)
→ On failure → auto-retry (up to 3x)
→ Still failing → AI analyzes
→ AI suggests fix → YOU approve → applies → retry

You sleep. Or at least know exactly what's broken.
```

**Tweet 4 (Demo):**
```
$ clockwork ci-run
▶ Stage 1: build ✓
▶ Stage 2: test ✗ FAIL

  → Retry 2/3... ✗
  → AI: "Add null check on line 42"
  ? Apply fix? (y/N): y
  
  ✓ All tests passed
```

**Tweet 5 (Why different):**
```
Why Clockwork != GitHub Actions:

• Runs locally (no waiting)
• Auto-retries (sane defaults)
• AI-assisted fixes (optional)
• Understand in 5 min (no YAML hell)
• Works WITHOUT AI (zero dependency)
```

**Tweet 6 (Key features):**
```
Features:
✓ Self-healing pipelines
✓ Local-first (no cloud)
✓ AI optional, always safe
✓ Simple YAML config
✓ Python 3.10+

pip install clockwork
```

**Tweet 7 (CTA):**
```
It's not for every team.

It's for when you just want to ship.

clockwork → the tool you reach for

🔗 github.com/ShibilAhamed701212/clockwork
```

---

## GitHub Optimization

---

### Repo Description (Short)

> Local-first CI/CD with self-healing pipelines. Works without AI. AI helps when you want it.

---

### 5 Tagline Variations

1. "CI/CD that heals itself when tests fail"
2. "Self-healing pipelines for solo developers"
3. "Local CI/CD that actually makes sense"
4. "The CI/CD tool you reach for when you just want to ship"
5. "Simple, local, reliable CI/CD with optional AI assistance"

---

### Pinned Tweet Description

```
Clockwork 🕐

CI/CD that fixes itself.

• Auto-retries on failure
• Optional AI fixes (you approve)
• Runs locally
• Works WITHOUT AI

pip install clockwork

github.com/ShibilAhamed701212/clockwork
```

---

## First 100 Users Plan

---

### Where to Post

| Platform | When | What |
|----------|------|------|
| r/programming | Week 1 | Launch post |
| r/python | Week 1 | Tool demo |
| Hacker News | Week 1 | Show HN |
| Twitter/X | Week 1-4 | Thread + replies |
| DEV.to | Week 2 | Tutorial |
| LinkedIn | Week 2 | Blog post |

### How to Respond

**Do:**
- Reply to every comment within 2 hours
- Ask clarifying questions
- Thank people for trying it
- Ask "what would make this useful for you?"
- Be honest about limitations

**Don't:**
- Get defensive about criticism
- Over-promote
- Ignore bug reports

### How to Gather Feedback

1. **GitHub Issues** - encourage bug reports
2. **Discussions** - feature requests
3. **Twitter DMs** - casual feedback
4. **Feedback form** - simple Google Form in README

### How to Iterate

1. **Daily:** Check issues, reply, fix critical bugs
2. **Weekly:** Ship minor improvements
3. **Bi-weekly:** Blog posts, updates
4. **Monthly:** Release new features

### First 100 Milestones

| Users | Action |
|-------|--------|
| 10 | Personal network + Twitter |
| 25 | Reddit launch + HN |
| 50 | DEV.to tutorial |
| 100 | Feature freeze + 1.0 planning |

---

## Trust Building Messaging

---

### On the Website/Repo Header

```
Clockwork 🕐
CI/CD that heals itself

[Install]
[GitHub ⭐]

Works without AI • You approve all fixes • Local-first
```

### AI Trust Section

```
## AI: It's Optional. Always.

✗ AI does NOT run automatically
✗ AI does NOT see your code without permission  
✗ AI does NOT apply fixes without approval

✓ Works perfectly without AI
✓ AI is opt-in only
✓ You approve EVERY change
✓ No external calls unless you configure it
```

### Safety Badge in README

```
[![Safe](https://img.shields.io/badge/AI-Optional-green)]()
[![Safe](https://img.shields.io/badge/Approval-Required-green)]()
[![Safe](https://img.shields.io/badge/Local--First-blue)]()
```

---

## Key Messaging Principles

1. **No hype** - honest about limitations
2. **No fake claims** - show real output
3. **Developer-first** - speak their language
4. **Simple** - scannable, not a novel
5. **Trust** - prove AI is optional, don't just say it
