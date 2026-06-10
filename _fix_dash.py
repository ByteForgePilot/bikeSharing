import re
path = r'E:\Project\personal\bikrsharing\backend\app\templates\index.html'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
# Remove the confidence row
c = c.replace('<span>置信度:</span><span id="f2-conf"></span>\n', '')
# Remove the hf_energy_ratio row
c = c.replace('<span>高频占比:</span><span id="f2-hf"></span>\n', '')
# Also remove the corresponding detail-header rows (tr containing these spans)
# Let me just remove the lines containing f2-conf and f2-hf
lines = c.split('\n')
lines = [l for l in lines if 'f2-conf' not in l and 'f2-hf' not in l]
c = '\n'.join(lines)
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print('Done')
