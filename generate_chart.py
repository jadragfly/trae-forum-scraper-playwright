#!/usr/bin/env python3
"""Generate ECharts visualization for Top 30 from RANKING.md data."""
import re, json, sys, os

def parse_ranking(filepath):
    """Extract Top N from ranking markdown table."""
    topics = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^\|\s*(\d+)\s*\|\s*\[(.+?)\]\((.+?)\)\s+\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|', line)
            if m:
                topics.append({
                    'rank': int(m.group(1)),
                    'title': m.group(2).strip(),
                    'url': m.group(3),
                    'votes': int(m.group(4)),
                    'replies': int(m.group(5)),
                    'views': int(m.group(6)),
                    'score': float(m.group(7))
                })
    return topics

def generate_chart_html(top30, output_path):
    """Generate an ECharts HTML with multiple charts for the Top 30."""
    chart_data = []
    for t in top30:
        label = t['title']
        if len(label) > 16:
            label = label[:14] + '..'
        chart_data.append({
            'rank': t['rank'],
            'title': label,
            'fullTitle': t['title'],
            'votes': t['votes'],
            'replies': t['replies'],
            'views': t['views'],
            'score': round(t['score'], 1)
        })

    data_json = json.dumps(chart_data, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trae技能创作赛 Top30 可视化</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#1a1a2e; color:#eee; font-family:system-ui,sans-serif; padding:20px; }}
h1 {{ text-align:center; color:#e94560; margin-bottom:8px; font-size:24px; }}
.subtitle {{ text-align:center; color:#888; font-size:13px; margin-bottom:24px; }}
.tabs {{ display:flex; justify-content:center; gap:4px; margin-bottom:16px; }}
.tabs button {{ background:#16213e; border:1px solid #333; color:#888; padding:8px 20px; border-radius:6px; cursor:pointer; font-size:13px; transition:0.15s; }}
.tabs button:hover {{ background:#1e2d4e; color:#ccc; }}
.tabs button.active {{ background:#e94560; color:#fff; border-color:#e94560; }}
.chart-box {{ display:none; background:#0d1b2a; border-radius:12px; padding:16px; border:1px solid #333; }}
.chart-box.active {{ display:block; }}
#chartA, #chartB {{ width:100%; height:560px; }}
#chartC {{ width:100%; height:800px; }}
.info-box {{ background:#0d1b2a; border-radius:12px; padding:16px; border:1px solid #333; margin-top:16px; font-size:13px; color:#aaa; line-height:1.8; }}
.info-box b {{ color:#e94560; }}
.data-ref {{ text-align:center; padding:20px; color:#555; font-size:12px; }}
</style>
</head>
<body>

<h1>Trae 技能创作赛 Top 30</h1>
<p class="subtitle">综合分 = 投票×3 + 回复×0.4 + 浏览×0.1</p>

<div class="tabs">
<button class="active" data-chart="A">三维对比柱状图</button>
<button data-chart="B">综合得分排名</button>
<button data-chart="C">散点图(投票 vs 浏览)</button>
</div>

<div class="chart-box active" id="boxA"><div id="chartA"></div></div>
<div class="chart-box" id="boxB"><div id="chartB"></div></div>
<div class="chart-box" id="boxC"><div id="chartC"></div></div>

<div class="info-box" id="infoBox">
  <b>评分算法：</b>综合分 = 投票数 × 3 + 回复数 × 0.4 + 浏览数 × 0.1<br>
  <b>投票：</b>权重最高(×3)，反映社区认可度<br>
  <b>回复：</b>权重(×0.4)，反映讨论热度<br>
  <b>浏览：</b>权重最低(×0.1)，反映曝光量
</div>

<div class="data-ref">数据来源: trae_skills/RANKING.md</div>

<script>
const RAW_DATA = {data_json};

// 格式化标题
function fmtTitle(t) {{
    // 去掉【Skill 创作】前缀
    let title = t.fullTitle.replace(/【[^】]*】\\s*/g, '').trim();
    if (title.length > 24) title = title.substring(0, 22) + '…';
    return title;
}}

const names = RAW_DATA.map(t => '#' + t.rank + ' ' + fmtTitle(t));

// === Tab 切换 ===
document.querySelectorAll('.tabs button').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.chart-box').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('box' + btn.dataset.chart).classList.add('active');
    setTimeout(() => {{ window.dispatchEvent(new Event('resize')); }}, 100);
  }});
}});

// === Chart A: 三维对比柱状图 ===
const chartA = echarts.init(document.getElementById('chartA'));
chartA.setOption({{
  tooltip: {{
    trigger: 'axis',
    axisPointer: {{ type: 'shadow' }},
    formatter: function(params) {{
      let idx = params[0].dataIndex;
      let t = RAW_DATA[idx];
      return '<b>#' + t.rank + ' ' + t.fullTitle + '</b><br>' +
        '投票: ' + t.votes + ' 票<br>' +
        '回复: ' + t.replies + ' 条<br>' +
        '浏览: ' + t.views + ' 次<br>' +
        '综合分: ' + t.score;
    }}
  }},
  legend: {{ data: ['投票数', '回复数', '浏览数(÷10)'], textStyle: {{ color: '#aaa' }} }},
  grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
  xAxis: {{ type: 'category', data: names, axisLabel: {{ rotate: 45, fontSize: 10, color: '#888' }} }},
  yAxis: {{ type: 'value', axisLabel: {{ color: '#888' }} }},
  series: [
    {{
      name: '投票数',
      type: 'bar',
      data: RAW_DATA.map(t => t.votes),
      itemStyle: {{ color: '#e94560' }},
      barWidth: 6
    }},
    {{
      name: '回复数',
      type: 'bar',
      data: RAW_DATA.map(t => t.replies),
      itemStyle: {{ color: '#0f3460' }},
      barWidth: 6
    }},
    {{
      name: '浏览数(÷10)',
      type: 'bar',
      data: RAW_DATA.map(t => Math.round(t.views / 10)),
      itemStyle: {{ color: '#533483' }},
      barWidth: 6
    }}
  ]
}});

// === Chart B: 综合得分排名 ===
const chartB = echarts.init(document.getElementById('chartB'));
chartB.setOption({{
  tooltip: {{
    trigger: 'axis',
    axisPointer: {{ type: 'shadow' }},
    formatter: function(params) {{
      let idx = params[0].dataIndex;
      let t = RAW_DATA[idx];
      return '<b>#' + t.rank + ' ' + t.fullTitle + '</b><br>' +
        '综合分: ' + t.score + '<br>' +
        '投票: ' + t.votes + ' | 回复: ' + t.replies + ' | 浏览: ' + t.views;
    }}
  }},
  grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
  xAxis: {{ type: 'category', data: names, axisLabel: {{ rotate: 45, fontSize: 10, color: '#888' }} }},
  yAxis: {{ type: 'value', name: '综合分', nameTextStyle: {{ color: '#888' }}, axisLabel: {{ color: '#888' }} }},
  series: [{{
    name: '综合分',
    type: 'bar',
    data: RAW_DATA.map(t => t.score),
    itemStyle: {{
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        {{ offset: 0, color: '#e94560' }},
        {{ offset: 1, color: '#533483' }}
      ])
    }},
    barWidth: 12,
    label: {{
      show: true,
      position: 'top',
      fontSize: 9,
      color: '#aaa',
      formatter: function(p) {{ return RAW_DATA[p.dataIndex].score; }}
    }}
  }}]
}});

// === Chart C: 散点图 ===
const chartC = echarts.init(document.getElementById('chartC'));
chartC.setOption({{
  tooltip: {{
    formatter: function(params) {{
      let t = RAW_DATA[params.dataIndex];
      return '<b>#' + t.rank + ' ' + t.fullTitle + '</b><br>' +
        '投票: ' + t.votes + ' 票<br>' +
        '回复: ' + t.replies + ' 条<br>' +
        '浏览: ' + t.views + ' 次<br>' +
        '综合分: ' + t.score;
    }}
  }},
  grid: {{ left: '4%', right: '4%', bottom: '14%', containLabel: true }},
  xAxis: {{ type: 'value', name: '投票数', nameTextStyle: {{ color: '#888' }}, axisLabel: {{ color: '#888' }} }},
  yAxis: {{ type: 'value', name: '浏览数', nameTextStyle: {{ color: '#888' }}, axisLabel: {{ color: '#888' }} }},
  series: [{{
    name: '技能分布',
    type: 'scatter',
    data: RAW_DATA.map(t => [t.votes, t.views, t.replies, t.score]),
    symbolSize: function(val) {{
      return Math.max(8, Math.min(32, val[2] * 0.8 + 8));
    }},
    itemStyle: {{
      color: function(params) {{
        var val = params.data[3];
        if (val >= 120) return '#e94560';
        if (val >= 90) return '#e97f45';
        if (val >= 60) return '#e9c545';
        return '#45b7e9';
      }}
    }},
    label: {{
      show: true,
      position: 'right',
      fontSize: 9,
      color: '#888',
      formatter: function(p) {{ return '#' + (p.dataIndex + 1); }}
    }}
  }}]
}});

window.addEventListener('resize', () => {{ chartA.resize(); chartB.resize(); chartC.resize(); }});
</script>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Chart HTML saved: {output_path}")
    return output_path

if __name__ == '__main__':
    ranking_file = os.path.join(os.path.dirname(__file__), 'trae_skills', 'RANKING.md')
    all_topics = parse_ranking(ranking_file)
    top30 = all_topics[:30]

    if len(top30) == 0:
        print("ERROR: No data parsed from ranking file!")
        # Debug: show first few lines of ranking file
        with open(ranking_file, 'r', encoding='utf-8') as f:
            content = f.read()
        print("File exists:", os.path.exists(ranking_file))
        print("Sample lines from ranking:")
        for line in content.split('\n')[7:12]:
            print(repr(line))
        sys.exit(1)

    output = os.path.join(os.path.dirname(__file__), 'trae_skills', 'top30_chart.html')
    generate_chart_html(top30, output)
    print(f"Done! Top {len(top30)} skills plotted.")