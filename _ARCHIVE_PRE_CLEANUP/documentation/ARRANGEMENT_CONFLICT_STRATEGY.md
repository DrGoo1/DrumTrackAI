# Arrangement Conflict Handling Strategy

## ✅ **Current Behavior (PROBLEM)**

**All three methods completely replace existing sections:**
- Auto-Analyze → `setSections(newSections)`
- Manual Entry → `setSections(newSections)`
- Well Known Song → `setSections(newSections)`

**Result:** Last method used wins, no warning to user!

---

## 🎯 **Recommended Solution**

### **Option 1: Confirmation Dialog (Recommended)**
```typescript
// Before applying new arrangement
if (sections.length > 0) {
  const confirmed = window.confirm(
    `You have ${sections.length} existing sections. 
    Replace with new arrangement?`
  );
  if (!confirmed) return;
}

setSections(newSections);
```

**Pros:**
- Simple and clear
- User has control
- Prevents accidental overwrites

**Cons:**
- Requires user interaction
- Browser confirm dialog not pretty

---

### **Option 2: Merge/Append Option**
```typescript
function handleManualArrangement(arrangement, mode: 'replace' | 'merge') {
  if (mode === 'merge') {
    setSections([...sections, ...newSections]);
  } else {
    setSections(newSections);
  }
}
```

**Pros:**
- Flexibility
- Can combine multiple sources

**Cons:**
- Complex UX
- Merge conflicts still possible
- Overlapping sections?

---

### **Option 3: Source Tracking + Visual Indicator**
```typescript
interface Section {
  // ... existing fields
  source: 'auto' | 'manual' | 'internet';
  sourceTimestamp: number;
}

// Show source in UI
<span className="text-xs">
  {section.source === 'auto' && '🎯 Auto-detected'}
  {section.source === 'manual' && '📝 Manual'}
  {section.source === 'internet' && '🌐 Internet'}
</span>
```

**Pros:**
- User knows where each section came from
- Can mix sources
- Transparency

**Cons:**
- More complex state management
- Still need conflict resolution

---

### **Option 4: "Arrangement Source" Selector**
```typescript
const [arrangementSource, setArrangementSource] = useState<'none' | 'auto' | 'manual' | 'internet'>('none');

// Lock arrangement once set
<div className="text-sm text-yellow-400">
  ⚠️ Current arrangement: {arrangementSource}
  <button onClick={clearArrangement}>Clear & Start Over</button>
</div>
```

**Pros:**
- Clear which method is active
- Prevents mixing
- Explicit "clear" action

**Cons:**
- Less flexible
- Can't switch methods easily

---

## 💡 **Recommended Implementation: Hybrid Approach**

### **Step 1: Add Confirmation with Source Tracking**

```typescript
const [arrangementSource, setArrangementSource] = useState<string | null>(null);

function applyArrangement(
  newSections: Section[], 
  source: string,
  sourceName: string
) {
  // Warn if replacing existing arrangement
  if (sections.length > 0 && arrangementSource) {
    const confirmed = window.confirm(
      `Replace ${arrangementSource} arrangement (${sections.length} sections) with ${sourceName} arrangement (${newSections.length} sections)?`
    );
    if (!confirmed) return;
  }
  
  setSections(newSections);
  setArrangementSource(sourceName);
  setErr(null);
}

// Use in handlers
function handleManualArrangement(arrangement: ManualArrangement) {
  const newSections = convertManualToSections(arrangement);
  applyArrangement(newSections, 'manual', 'Manual Entry');
}

function handleSongLookup(songInfo: SongInfo) {
  const newSections = convertLookupToSections(songInfo);
  applyArrangement(newSections, 'internet', `"${songInfo.title}" by ${songInfo.artist}`);
}

async function handleAutoSectionize(trackKey: string) {
  // ... analyze ...
  applyArrangement(analyzedSections, 'auto', 'Auto-Analyze');
}
```

### **Step 2: Show Current Source in UI**

```tsx
{arrangementSource && sections.length > 0 && (
  <div className="p-2 bg-blue-900/20 border border-blue-700/50 rounded text-xs text-blue-300">
    📊 Current arrangement: {arrangementSource} ({sections.length} sections)
    <button 
      onClick={clearArrangement}
      className="ml-2 px-2 py-0.5 bg-red-600/20 hover:bg-red-600/40 rounded"
    >
      Clear
    </button>
  </div>
)}
```

### **Step 3: Add Clear Function**

```typescript
function clearArrangement() {
  const confirmed = window.confirm('Clear all sections?');
  if (!confirmed) return;
  
  setSections([]);
  setArrangementSource(null);
  setSongMap(null);
}
```

---

## 🎨 **UI Flow Examples**

### **Scenario 1: User has no arrangement**
```
State: sections.length === 0

[🎯 Auto-Analyze (AI)]  ← Enabled
[📝 Manual Entry]       ← Enabled  
[🌐 Well Known Song]    ← Enabled

No warning needed, just apply.
```

---

### **Scenario 2: User clicks second method**
```
State: sections.length === 16 (from Auto-Analyze)

User clicks "📝 Manual Entry"
  ↓
⚠️ Confirmation Dialog:
"Replace Auto-Analyze arrangement (16 sections) 
 with Manual Entry arrangement?"
[Cancel] [Replace]

If Cancel → Keep existing
If Replace → Apply new, update source
```

---

### **Scenario 3: Current arrangement displayed**
```
┌────────────────────────────────────┐
│ 📊 Current: Auto-Analyze (16)      │
│                          [Clear]    │
├────────────────────────────────────┤
│ [🎯 Auto-Analyze (AI)]             │
│ [📝 Manual Entry]                  │
│ [🌐 Well Known Song]               │
└────────────────────────────────────┘
```

---

## 🔧 **Implementation Priority**

### **Phase 1: Essential (Now)**
- [x] Add confirmation before overwriting
- [x] Track arrangement source
- [x] Display current source in UI

### **Phase 2: Enhanced (Later)**
- [ ] "Clear Arrangement" button
- [ ] Source indicator per section
- [ ] Merge option for advanced users
- [ ] Undo/redo functionality

---

## 📝 **Code Changes Needed**

### **Files to Modify:**

1. **`WebDAWApp.tsx`**
   - Add `arrangementSource` state
   - Add `applyArrangement()` helper
   - Update all three handlers
   - Add confirmation logic
   - Add UI indicator

2. **`SectionControls.tsx`**
   - Show arrangement source
   - Add clear button
   - Optional: source badge per section

3. **Type Definitions**
   - Add `source` field to `Section` interface (optional)

---

## ✅ **Benefits**

1. **No accidental data loss** - User is warned before overwrite
2. **Clear current state** - User knows which method is active
3. **Easy to switch** - Just confirm and replace
4. **Transparent** - Source is always visible
5. **Simple UX** - One confirmation dialog

---

## 🚀 **Ready to Implement?**

This hybrid approach provides:
- ✅ Safety (confirmation)
- ✅ Clarity (source tracking)
- ✅ Simplicity (one dialog)
- ✅ Flexibility (can still switch methods)

Would you like me to implement this now?
