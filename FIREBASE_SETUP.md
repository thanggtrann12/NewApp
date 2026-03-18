# Firebase setup for mobile sync/control

This app already supports Firebase Realtime Database through `transport/firebase_transport.py`.

Project values you shared:

- projectId: `watering-automation-b6120`
- databaseURL: `https://watering-automation-b6120-default-rtdb.firebaseio.com`
- authDomain: `watering-automation-b6120.firebaseapp.com`

## 1. Create Firebase project + Realtime Database

1. Open Firebase Console.
2. Create project.
3. Enable Realtime Database.
4. Choose region close to your deployment.

## 2. Create service account key (for this Python app)

1. Firebase Console -> Project settings -> Service accounts.
2. Generate new private key.
3. Save JSON key to a secure local path, for example:
  `C:/secrets/watering-automation-b6120-firebase-adminsdk.json`

## 3. Install Python dependency

```bash
pip install firebase-admin
```

## 4. Create local runtime config

Create `data/firebase_config.json` (do not commit this file):

```json
{
  "credential": "C:/secrets/watering-automation-b6120-firebase-adminsdk.json",
  "database_url": "https://watering-automation-b6120-default-rtdb.firebaseio.com"
}
```

A template is available at `data/firebase_config.example.json`.

## 5. Realtime Database rules (basic)

Use Firebase Auth on mobile app and start with:

```json
{
  "rules": {
    "irrigation": {
      ".read": "auth != null",
      ".write": "auth != null"
    }
  }
}
```

For production, restrict by UID/role as needed.

## 5.1 Flutter app side (from your FirebaseOptions)

Your Flutter `FirebaseOptions` are already enough to connect mobile app to the same project.
The Python backend does not use apiKey/appId. It only needs:

- service account JSON (`credential`)
- realtime database URL (`database_url`)

In Flutter, after `Firebase.initializeApp(...)`, use Realtime Database refs under root `irrigation`.

Example refs:

- Read zones list: `FirebaseDatabase.instance.ref("irrigation/zones")`
- Listen live pump state: `FirebaseDatabase.instance.ref("irrigation/nodes/{nodeId}/pump_state/{pumpIdx}")`
- Send control command: `FirebaseDatabase.instance.ref("irrigation/commands/{nodeId}/{pumpIdx}").set({"cmd": "ON", "ts": DateTime.now().toIso8601String()})`

## 6. Data paths used by this app

Root path: `irrigation`

- Sensor data (Pi -> Firebase):
  - `irrigation/nodes/{nodeId}/sensor/{pumpIdx}`
  - payload example:
    `{ "moisture": 72.1, "temperature": 27.0, "humidity": 61.0, "_ts": "2026-03-12T09:30:10" }`

- Pump state (Pi -> Firebase):
  - `irrigation/nodes/{nodeId}/pump_state/{pumpIdx}`
  - payload example:
    `{ "state": "ON", "_ts": "2026-03-12T09:30:12" }`

- Node config (Pi -> Firebase):
  - `irrigation/nodes/{nodeId}/config`
  - mobile can also write this path to update timer/schedule directly

- Zones mapping (Pi -> Firebase):
  - `irrigation/zones/{zoneId}`
  - `irrigation/zones_meta`

- Remote command (mobile -> Pi):
  - `irrigation/commands/{nodeId}/{pumpIdx}`
  - payload example:
    `{ "cmd": "ON", "ts": "2026-03-12T09:31:00" }`

After command is consumed, this app deletes that command entry.

## 7. Mobile app control flow

1. Mobile writes command to `irrigation/commands/{nodeId}/{pumpIdx}`.
2. Python app receives it via Firebase listener.
3. Python app sends command to device through serial transport.
4. Device state updates come back and are published to `pump_state`.
5. Mobile listens `pump_state` for confirmation.

## 7.2 Mobile update TIMER/SCHEDULE config directly

Write to:

- `irrigation/nodes/{nodeId}/config`

Payload example:

```json
{
  "name": "pumpB2CE",
  "pumps": 4,
  "pump_config": {
    "0": {
      "mode": "AUTO",
      "auto_type": "TIMER",
      "crop_id": "tomato",
      "schedule": [
        {"time": "06:30", "duration": 8, "days": [0,1,2,3,4,5,6]},
        {"time": "18:00", "duration": 6, "days": []}
      ]
    }
  }
}
```

Notes:

- `auto_type` supports `SCHEDULE` or `TIMER`.
- `schedule[].days`: empty means every day.
- After mobile writes config, backend applies it to local store and UI refreshes automatically.

## 7.1 Minimal Flutter control snippet

```dart
Future<void> sendPumpCommand({
  required String nodeId,
  required int pumpIdx,
  required String cmd, // "ON" or "OFF"
}) async {
  final ref = FirebaseDatabase.instance
      .ref('irrigation/commands/$nodeId/$pumpIdx');

  await ref.set({
    'cmd': cmd,
    'ts': DateTime.now().toIso8601String(),
  });
}

Stream<Map?> watchPumpState(String nodeId, int pumpIdx) {
  final ref = FirebaseDatabase.instance
      .ref('irrigation/nodes/$nodeId/pump_state/$pumpIdx');

  return ref.onValue.map((e) => e.snapshot.value as Map?);
}
```

## 8. Run and verify

1. Start this Python app.
2. Check console for `[FIREBASE] transport started`.
3. In Firebase console, verify nodes appear under `irrigation`.
4. From mobile app, write test command and confirm pump state changes.
