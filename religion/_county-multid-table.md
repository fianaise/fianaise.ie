<!-- Written by analysis/charts/make_maps.py from the school-level survey results. Don't edit by hand. -->
<style>
#county-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.88rem;
  font-variant-numeric: tabular-nums; line-height: 1.3; margin: 0; }
#county-table th, #county-table td { padding: 0.42rem 0.6rem; text-align: right; white-space: nowrap;
  border-bottom: 1px solid #e8e7e3; vertical-align: middle; }
#county-table th:first-child, #county-table td:first-child { text-align: left; padding-left: 0.5rem; min-width: 6.5rem;
  position: sticky; left: 0; background: inherit; z-index: 1; }
#county-table thead th { font-weight: 600; color: #0b0b0b; vertical-align: bottom; white-space: normal; }
#county-table thead tr:last-child th { border-bottom: 2px solid #0b0b0b; background: #fff; }
#county-table .group-row th { text-align: center; font-size: 0.82rem; border-bottom: 2px solid #c9c7c0; padding-bottom: 0.3rem; }
#county-table .group-row th span { display: block; font-weight: 400; color: #52514e; font-size: 0.76rem; }
#county-table .group-row .is-cur { border-bottom-color: #eb6834; }
#county-table .group-row .is-pre { border-bottom-color: #f4b183; }
#county-table .group-row td { border-bottom: 0; background: #fff; }
#county-table .grp { border-left: 1px solid #e8e7e3; }
#county-table tbody tr { background: #fff; }
#county-table tbody tr:nth-child(even) { background: #f8f7f4; }
#county-table tbody tr:hover { background: #f1efe9; }
#county-table tbody th { font-weight: 600; }
#county-table tfoot tr { background: #fff; }
#county-table tfoot th, #county-table tfoot td { font-weight: 700; border-top: 2px solid #0b0b0b; border-bottom: 0; }
#county-table thead tr:last-child th { cursor: pointer; user-select: none; }
#county-table th[aria-sort="ascending"]::after { content: " \25B2"; font-size: 0.65em; }
#county-table th[aria-sort="descending"]::after { content: " \25BC"; font-size: 0.65em; }
#county-table .pct-bar { display: inline-block; width: 3rem; height: 0.5rem; margin-right: 0.45rem; vertical-align: middle;
  border-radius: 2px; background: linear-gradient(to right, #eb6834 var(--pct), #ecebe6 var(--pct)); }
#county-table .pct-bar.is-pre { background: linear-gradient(to right, #f4b183 var(--pct), #ecebe6 var(--pct)); }
.data-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 0.75rem 0 0.25rem;
  border-top: 1px solid #e8e7e3; }
@media (max-width: 575px) {
  #county-table { font-size: 0.8rem; }
  #county-table th, #county-table td { padding: 0.38rem 0.45rem; }
  #county-table .pct-bar { display: none; }
}
</style>
<div class="data-table-wrap" data-figure="county_denominational_multid">
<table class="data-table sortable" id="county-table">
<thead><tr class="group-row"><td></td><th scope="colgroup" colspan="4">Mainstream denominational schools</th><th scope="colgroup" colspan="2" class="grp is-cur">Current households<span>more than 50% want multi-denominational</span></th><th scope="colgroup" colspan="2" class="grp is-pre">Current and preschool households<span>50% or more want multi-denominational</span></th></tr>
<tr><th scope="col">County</th><th scope="col">All</th><th scope="col">Catholic</th><th scope="col">Other faiths</th><th scope="col">With results</th><th scope="col" class="grp">Schools</th><th scope="col">Share</th><th scope="col" class="grp">Schools</th><th scope="col">Share</th></tr></thead>
<tbody>
<tr><th scope="row">Wicklow</th><td>76</td><td>55</td><td>21</td><td>75</td><td class="grp">36</td><td data-value="48.00"><span class="pct-bar" style="--pct:48.0%"></span>48.0%</td><td class="grp">40</td><td data-value="53.33"><span class="pct-bar is-pre" style="--pct:53.3%"></span>53.3%</td></tr>
<tr><th scope="row">Cork</th><td>321</td><td>302</td><td>19</td><td>307</td><td class="grp">97</td><td data-value="31.60"><span class="pct-bar" style="--pct:31.6%"></span>31.6%</td><td class="grp">104</td><td data-value="33.88"><span class="pct-bar is-pre" style="--pct:33.9%"></span>33.9%</td></tr>
<tr><th scope="row">Dublin</th><td>387</td><td>346</td><td>41</td><td>386</td><td class="grp">113</td><td data-value="29.27"><span class="pct-bar" style="--pct:29.3%"></span>29.3%</td><td class="grp">121</td><td data-value="31.35"><span class="pct-bar is-pre" style="--pct:31.3%"></span>31.3%</td></tr>
<tr><th scope="row">Waterford</th><td>71</td><td>67</td><td>4</td><td>68</td><td class="grp">19</td><td data-value="27.94"><span class="pct-bar" style="--pct:27.9%"></span>27.9%</td><td class="grp">23</td><td data-value="33.82"><span class="pct-bar is-pre" style="--pct:33.8%"></span>33.8%</td></tr>
<tr><th scope="row">Kildare</th><td>91</td><td>83</td><td>8</td><td>90</td><td class="grp">20</td><td data-value="22.22"><span class="pct-bar" style="--pct:22.2%"></span>22.2%</td><td class="grp">24</td><td data-value="26.67"><span class="pct-bar is-pre" style="--pct:26.7%"></span>26.7%</td></tr>
<tr><th scope="row">Kilkenny</th><td>67</td><td>65</td><td>2</td><td>65</td><td class="grp">14</td><td data-value="21.54"><span class="pct-bar" style="--pct:21.5%"></span>21.5%</td><td class="grp">17</td><td data-value="26.15"><span class="pct-bar is-pre" style="--pct:26.2%"></span>26.2%</td></tr>
<tr><th scope="row">Sligo</th><td>61</td><td>57</td><td>4</td><td>57</td><td class="grp">12</td><td data-value="21.05"><span class="pct-bar" style="--pct:21.1%"></span>21.1%</td><td class="grp">13</td><td data-value="22.81"><span class="pct-bar is-pre" style="--pct:22.8%"></span>22.8%</td></tr>
<tr><th scope="row">Clare</th><td>106</td><td>105</td><td>1</td><td>90</td><td class="grp">17</td><td data-value="18.89"><span class="pct-bar" style="--pct:18.9%"></span>18.9%</td><td class="grp">20</td><td data-value="22.22"><span class="pct-bar is-pre" style="--pct:22.2%"></span>22.2%</td></tr>
<tr><th scope="row">Galway</th><td>209</td><td>207</td><td>2</td><td>181</td><td class="grp">29</td><td data-value="16.02"><span class="pct-bar" style="--pct:16.0%"></span>16.0%</td><td class="grp">32</td><td data-value="17.68"><span class="pct-bar is-pre" style="--pct:17.7%"></span>17.7%</td></tr>
<tr><th scope="row">Westmeath</th><td>71</td><td>66</td><td>5</td><td>67</td><td class="grp">10</td><td data-value="14.93"><span class="pct-bar" style="--pct:14.9%"></span>14.9%</td><td class="grp">9</td><td data-value="13.43"><span class="pct-bar is-pre" style="--pct:13.4%"></span>13.4%</td></tr>
<tr><th scope="row">Wexford</th><td>95</td><td>91</td><td>4</td><td>95</td><td class="grp">14</td><td data-value="14.74"><span class="pct-bar" style="--pct:14.7%"></span>14.7%</td><td class="grp">20</td><td data-value="21.05"><span class="pct-bar is-pre" style="--pct:21.1%"></span>21.1%</td></tr>
<tr><th scope="row">Leitrim</th><td>37</td><td>34</td><td>3</td><td>35</td><td class="grp">5</td><td data-value="14.29"><span class="pct-bar" style="--pct:14.3%"></span>14.3%</td><td class="grp">5</td><td data-value="14.29"><span class="pct-bar is-pre" style="--pct:14.3%"></span>14.3%</td></tr>
<tr><th scope="row">Cavan</th><td>73</td><td>64</td><td>9</td><td>68</td><td class="grp">8</td><td data-value="11.76"><span class="pct-bar" style="--pct:11.8%"></span>11.8%</td><td class="grp">9</td><td data-value="13.24"><span class="pct-bar is-pre" style="--pct:13.2%"></span>13.2%</td></tr>
<tr><th scope="row">Kerry</th><td>125</td><td>123</td><td>2</td><td>116</td><td class="grp">12</td><td data-value="10.34"><span class="pct-bar" style="--pct:10.3%"></span>10.3%</td><td class="grp">16</td><td data-value="13.79"><span class="pct-bar is-pre" style="--pct:13.8%"></span>13.8%</td></tr>
<tr><th scope="row">Laois</th><td>62</td><td>55</td><td>7</td><td>60</td><td class="grp">6</td><td data-value="10.00"><span class="pct-bar" style="--pct:10.0%"></span>10.0%</td><td class="grp">9</td><td data-value="15.00"><span class="pct-bar is-pre" style="--pct:15.0%"></span>15.0%</td></tr>
<tr><th scope="row">Tipperary</th><td>150</td><td>144</td><td>6</td><td>142</td><td class="grp">14</td><td data-value="9.86"><span class="pct-bar" style="--pct:9.9%"></span>9.9%</td><td class="grp">20</td><td data-value="14.08"><span class="pct-bar is-pre" style="--pct:14.1%"></span>14.1%</td></tr>
<tr><th scope="row">Meath</th><td>105</td><td>100</td><td>5</td><td>102</td><td class="grp">10</td><td data-value="9.80"><span class="pct-bar" style="--pct:9.8%"></span>9.8%</td><td class="grp">15</td><td data-value="14.71"><span class="pct-bar is-pre" style="--pct:14.7%"></span>14.7%</td></tr>
<tr><th scope="row">Carlow</th><td>41</td><td>37</td><td>4</td><td>41</td><td class="grp">4</td><td data-value="9.76"><span class="pct-bar" style="--pct:9.8%"></span>9.8%</td><td class="grp">4</td><td data-value="9.76"><span class="pct-bar is-pre" style="--pct:9.8%"></span>9.8%</td></tr>
<tr><th scope="row">Mayo</th><td>148</td><td>146</td><td>2</td><td>125</td><td class="grp">12</td><td data-value="9.60"><span class="pct-bar" style="--pct:9.6%"></span>9.6%</td><td class="grp">18</td><td data-value="14.40"><span class="pct-bar is-pre" style="--pct:14.4%"></span>14.4%</td></tr>
<tr><th scope="row">Limerick</th><td>130</td><td>127</td><td>3</td><td>127</td><td class="grp">11</td><td data-value="8.66"><span class="pct-bar" style="--pct:8.7%"></span>8.7%</td><td class="grp">14</td><td data-value="11.02"><span class="pct-bar is-pre" style="--pct:11.0%"></span>11.0%</td></tr>
<tr><th scope="row">Donegal</th><td>170</td><td>136</td><td>34</td><td>144</td><td class="grp">12</td><td data-value="8.33"><span class="pct-bar" style="--pct:8.3%"></span>8.3%</td><td class="grp">20</td><td data-value="13.89"><span class="pct-bar is-pre" style="--pct:13.9%"></span>13.9%</td></tr>
<tr><th scope="row">Roscommon</th><td>86</td><td>84</td><td>2</td><td>70</td><td class="grp">4</td><td data-value="5.71"><span class="pct-bar" style="--pct:5.7%"></span>5.7%</td><td class="grp">7</td><td data-value="10.00"><span class="pct-bar is-pre" style="--pct:10.0%"></span>10.0%</td></tr>
<tr><th scope="row">Offaly</th><td>65</td><td>62</td><td>3</td><td>64</td><td class="grp">3</td><td data-value="4.69"><span class="pct-bar" style="--pct:4.7%"></span>4.7%</td><td class="grp">5</td><td data-value="7.81"><span class="pct-bar is-pre" style="--pct:7.8%"></span>7.8%</td></tr>
<tr><th scope="row">Louth</th><td>65</td><td>62</td><td>3</td><td>65</td><td class="grp">2</td><td data-value="3.08"><span class="pct-bar" style="--pct:3.1%"></span>3.1%</td><td class="grp">3</td><td data-value="4.62"><span class="pct-bar is-pre" style="--pct:4.6%"></span>4.6%</td></tr>
<tr><th scope="row">Monaghan</th><td>62</td><td>53</td><td>9</td><td>58</td><td class="grp">1</td><td data-value="1.72"><span class="pct-bar" style="--pct:1.7%"></span>1.7%</td><td class="grp">3</td><td data-value="5.17"><span class="pct-bar is-pre" style="--pct:5.2%"></span>5.2%</td></tr>
<tr><th scope="row">Longford</th><td>37</td><td>34</td><td>3</td><td>33</td><td class="grp">0</td><td data-value="0.00"><span class="pct-bar" style="--pct:0.0%"></span>0.0%</td><td class="grp">2</td><td data-value="6.06"><span class="pct-bar is-pre" style="--pct:6.1%"></span>6.1%</td></tr>
</tbody>
<tfoot>
<tr class="total"><th scope="row">Ireland</th><td>2,911</td><td>2,705</td><td>206</td><td>2,731</td><td class="grp">485</td><td data-value="17.76"><span class="pct-bar" style="--pct:17.8%"></span>17.8%</td><td class="grp">573</td><td data-value="20.98"><span class="pct-bar is-pre" style="--pct:21.0%"></span>21.0%</td></tr>
</tfoot>
</table>
</div>
