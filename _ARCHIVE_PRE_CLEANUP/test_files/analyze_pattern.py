import json

# Read and check file content
with open('test_pattern.json', 'rb') as f:
    raw = f.read()
    print(f'File size: {len(raw)} bytes')
    print(f'First 100 bytes: {raw[:100]}')
    
with open('test_pattern.json', 'r', encoding='utf-16') as f:
    content = f.read()
    if not content:
        print('ERROR: File is empty!')
        exit(1)
    print(f'Content length: {len(content)} chars')
    data = json.loads(content)

notes = data['notes']
print(f'Total notes: {len(notes)}')

# Count by lane
lanes = {}
for n in notes:
    lane = n['lane']
    lanes[lane] = lanes.get(lane, 0) + 1

print('\nNotes per drum:')
for lane, count in sorted(lanes.items()):
    print(f'  {lane:8s}: {count:4d} notes')

# Show timing spread
if notes:
    times = [n['time'] for n in notes]
    print(f'\nTime range: {min(times):.2f}s - {max(times):.2f}s')
    print(f'Duration: {max(times) - min(times):.2f}s')

# Sample first 10 notes
print('\nFirst 10 notes:')
for i, note in enumerate(notes[:10]):
    print(f"  {i+1}. {note['lane']:8s} @ {note['time']:6.2f}s  vel={note['vel']:.2f}")
