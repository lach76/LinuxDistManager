/**
 * Created by kimjh on 15. 12. 15.
 */
$(document).ready(function() {
	$(chart_id).highcharts({
		chart: chart,
		title: title,
		xAxis: xAxis,
		yAxis: yAxis,
		series: series
	});
});