
# Threat Model: AI-Driven Zero-Trust Behavior Firewall (ZTBF)

---

## Executive Summary

This threat model defines the adversarial landscape that ZTBF is designed to defend against. Traditional security controls (firewalls, IDS, antivirus) fail to detect **behavior-based threats** where attackers use legitimate credentials and authorized access patterns. ZTBF addresses this gap through continuous behavioral verification.

---

## Threat Model Assumptions

### In-Scope Assets
- User identities (employees, contractors, admins)
- Service accounts and API keys
- Cloud resources (compute, storage, databases)
- Internal APIs and microservices
- Sensitive data repositories
- Administrative interfaces

### Out-of-Scope (Phase 0)
- Physical security
- Social engineering detection
- Malware analysis
- DDoS attacks
- Zero-day exploits in applications

### Attacker Profiles

| Profile | Capability | Motivation | Access Level |
|---------|-----------|------------|--------------|
| **External Attacker (Post-Compromise)** | High technical skill, stolen credentials | Financial gain, espionage | Valid user credentials |
| **Malicious Insider** | Intimate system knowledge, legitimate access | Revenge, financial gain, ideology | Authorized user account |
| **Compromised Service Account** | Automated access, API tokens | Pivot point for lateral movement | Service-level privileges |
| **Negligent Insider** | Low security awareness | Unintentional harm | Standard user access |
| **Advanced Persistent Threat (APT)** | State-sponsored, patient, sophisticated | Long-term espionage | Multiple compromised accounts |

---

## Threat Scenarios

### 1. CREDENTIAL THEFT & MISUSE (Priority 1)

#### Scenario 1.1: Stolen Password Reuse
**Attack Flow:**
```
Attacker obtains credentials → Logs in from new location → 
Accesses resources normally restricted → Downloads sensitive data
```

**Traditional Firewall Blindspot:**
- Valid credentials = Valid traffic
- Network-level firewalls see authorized IP/port combinations
- No visibility into authentication context or access patterns

**ZTBF Detection Signals:**
- Geographic impossibility (login from US, then China 10 minutes later)
- Device fingerprint mismatch
- Time-of-day anomaly (access at 3 AM, user normally 9-5)
- Resource access deviation (accessing financial DB, never done before)

**Impact:** HIGH - Direct data breach, compliance violation

---

#### Scenario 1.2: Token/Session Hijacking
**Attack Flow:**
```
Attacker steals API token/JWT → Uses token to access APIs → 
Enumerates resources → Exfiltrates data via legitimate API calls
```

**Traditional Firewall Blindspot:**
- API traffic appears legitimate (valid token, proper TLS)
- Rate limits may not trigger for low-and-slow attacks

**ZTBF Detection Signals:**
- API call sequence anomaly (unusual endpoint combinations)
- Velocity anomaly (10x normal API call rate)
- Resource enumeration pattern (sequential ID scanning)
- Data volume anomaly (downloading entire customer table)

**Impact:** HIGH - API abuse, mass data exfiltration

---

### 2. LATERAL MOVEMENT (Priority 2)

#### Scenario 2.1: East-West Service Exploitation
**Attack Flow:**
```
Attacker compromises web server → Uses service account to access database → 
Pivots to adjacent microservices → Establishes persistence
```

**Traditional Firewall Blindspot:**
- Internal network traffic often less scrutinized
- Service-to-service calls expected and allowed
- No behavior baseline for service accounts

**ZTBF Detection Signals:**
- Service dependency graph violation (service A never calls service D)
- Unusual database query patterns (admin queries from app service)
- Time-based anomaly (batch service active during business hours)
- Cross-zone access (frontend service accessing backend admin API)

**Impact:** CRITICAL - Full environment compromise, persistent access

---

#### Scenario 2.2: Privilege Escalation via Cloud APIs
**Attack Flow:**
```
Attacker gains low-privilege access → Enumerates IAM policies → 
Exploits misconfigured role → Assumes admin privileges → 
Modifies security groups, creates backdoor accounts
```

**Traditional Firewall Blindspot:**
- Cloud API calls are legitimate HTTPS traffic
- IAM operations appear as normal administrative activity

**ZTBF Detection Signals:**
- IAM enumeration pattern (listing roles, policies, permissions)
- Privilege modification attempts (updating assume-role policies)
- New credential creation (API key generation spike)
- Security policy changes (firewall rule modifications)

**Impact:** CRITICAL - Admin-level compromise, environment takeover

---

### 3. PRIVILEGE ESCALATION (Priority 3)

#### Scenario 3.1: Abuse of Legitimate Admin Access
**Attack Flow:**
```
Compromised admin account → Accesses production systems → 
Disables logging → Modifies security controls → Creates backdoor
```

**Traditional Firewall Blindspot:**
- Admin traffic is expected to have broad access
- Privileged actions are technically authorized

**ZTBF Detection Signals:**
- Admin action velocity anomaly (100 changes in 10 minutes)
- Logging/monitoring tampering (CloudTrail disabled)
- Off-hours privileged access (admin login at 2 AM)
- Bulk privilege grants (adding admin rights to 50 accounts)

**Impact:** CRITICAL - Security control bypass, persistent backdoor

---

### 4. INSIDER THREATS (Priority 4)

#### Scenario 4.1: Malicious Data Exfiltration
**Attack Flow:**
```
Disgruntled employee → Downloads customer database → 
Uploads to personal cloud storage → Sells data on dark web
```

**Traditional Firewall Blindspot:**
- Employee has legitimate access to the data
- HTTPS upload to cloud storage is normal encrypted traffic

**ZTBF Detection Signals:**
- Data access volume spike (querying 100K records vs. normal 50)
- Unusual data export (downloading full tables, not typical workflow)
- Upload to external service (Dropbox, personal email)
- Pre-termination behavior pattern (access spike before last day)

**Impact:** HIGH - Data breach, regulatory fines, reputational damage

---

#### Scenario 4.2: Insider Reconnaissance
**Attack Flow:**
```
Employee explores unauthorized areas → Tests access boundaries → 
Maps network architecture → Prepares for attack or sells intelligence
```

**Traditional Firewall Blindspot:**
- Exploration appears as normal browsing/navigation
- No malicious payload detected

**ZTBF Detection Signals:**
- Access pattern deviation (visiting admin panels, unusual apps)
- Failed authorization attempts (trying restricted resources)
- Documentation access (reading security policies, architecture docs)
- Screenshot/documentation tools usage

**Impact:** MEDIUM - Preparation for larger attack, information gathering

---

### 5. DATA EXFILTRATION (Priority 5)

#### Scenario 5.1: Low-and-Slow Data Theft
**Attack Flow:**
```
Attacker exfiltrates small amounts daily → Stays under DLP thresholds → 
Uses DNS tunneling or steganography → Evades traditional detection
```

**Traditional Firewall Blindspot:**
- Small data transfers don't trigger volume alerts
- Encrypted traffic hides payload content

**ZTBF Detection Signals:**
- Consistent small-volume anomaly (daily 100 MB download, never before)
- Unusual protocol usage (DNS query volume spike)
- Time-series pattern (exfiltration every night at 11 PM)
- Destination anomaly (connections to rare/new external IPs)

**Impact:** MEDIUM-HIGH - Slow but successful data theft

---

## Why Traditional Firewalls Fail

### Network Firewalls (L3/L4)
**Limitation:** Only see IP addresses, ports, protocols
- ❌ No identity awareness
- ❌ No behavior context
- ❌ No understanding of application logic
- ❌ Allow all traffic from authenticated users

### Web Application Firewalls (L7)
**Limitation:** Focus on malicious payloads, not behavior
- ❌ Miss legitimate credential misuse
- ❌ No cross-session analysis
- ❌ No user behavior baselining
- ❌ Signature-based, not anomaly-based

### Next-Gen Firewalls (NGFW)
**Limitation:** Still network-centric
- ❌ Limited cloud API visibility
- ❌ No service-to-service behavior modeling
- ❌ No identity-centric policies
- ❌ Reactive rules, not predictive analytics

### Identity-Aware Proxies
**Limitation:** Static policy enforcement
- ✅ Identity verification (good)
- ❌ No dynamic behavior analysis
- ❌ No risk scoring
- ❌ No temporal/contextual awareness

---

## ZTBF Value Proposition

### What ZTBF Detects That Others Miss

| Attack Type | Traditional Security | ZTBF Advantage |
|-------------|---------------------|----------------|
| Valid credential misuse | ❌ Allowed | ✅ Behavioral anomaly detected |
| Insider data theft | ❌ Authorized access | ✅ Volume/pattern anomaly |
| Lateral movement | ❌ Internal traffic allowed | ✅ Service graph violation |
| Privilege escalation | ❌ Admin traffic permitted | ✅ Action velocity anomaly |
| API abuse | ❌ Valid token accepted | ✅ Sequence/velocity anomaly |
| Low-and-slow exfiltration | ❌ Under threshold | ✅ Time-series pattern detected |

### Core Detection Principles

1. **Identity-Centric**: Every action tied to a user/service identity
2. **Behavior-Based**: Detect deviations from learned normal patterns
3. **Context-Aware**: Consider time, location, device, resource sensitivity
4. **Graph-Aware**: Understand entity relationships and dependencies
5. **Temporal**: Analyze sequences and time-series patterns
6. **Adaptive**: Models evolve as legitimate behavior changes

---

## Trust Assumptions

### What We Trust (Initially)
- Identity provider authentication (assume MFA enforced)
- Logging infrastructure integrity (CloudTrail, Azure AD logs)
- Time synchronization (NTP-based timestamps accurate)
- Initial baseline period data quality

### What We Never Trust
- That valid credentials = legitimate user
- That authorized access = appropriate action
- That internal traffic = safe traffic
- That past behavior guarantees future intent
- That a single signal determines risk

### Progressive Trust Model
```
New Entity → Low Trust (restrictive, high scrutiny)
    ↓ (30 days baseline)
Established Pattern → Medium Trust (normal access, moderate monitoring)
    ↓ (continued good behavior)
Trusted Entity → High Trust (streamlined access, anomaly-focused monitoring)
    ↓ (any suspicious behavior)
Re-evaluation → Trust reduced, enhanced monitoring
```