const renderChart = (data, labels) => {
    var ctx = document.getElementById("myChart").getContext("2d");
    var myChart = new Chart(ctx, {
        type: "pie",
        data: {
            labels: labels,
            datasets: [{
                label: "Last 6 months expenses",
                data: data,
                backgroundColor: [
                    "rgba(255, 99, 132, 0.2)",
                    "rgba(54, 162, 235, 0.2)",
                    "rgba(255, 206, 86, 0.2)",
                    "rgba(75, 192, 192, 0.2)",
                    "rgba(153, 102, 255, 0.2)",
                    "rgba(255, 159, 64, 0.2)",
                ],
                borderColor: [
                    "rgba(255, 99, 132, 1)",
                    "rgba(54, 162, 235, 1)",
                    "rgba(255, 206, 86, 1)",
                    "rgba(75, 192, 192, 1)",
                    "rgba(153, 102, 255, 1)",
                    "rgba(255, 159, 64, 1)",
                ],
                borderWidth: 1,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            title: {
                display: true,
                text: "Expenses per category",
            },
        },
    });
};

const getChartData = () => {
    console.log("Fetching data...");
    fetch("/expense_category_summary")
        .then((res) => res.json())
        .then((results) => {
            console.log("Received data:", results);
            const category_data = results.expense_category_data;
            const labels = Object.keys(category_data);
            const data = Object.values(category_data);

            renderChart(data, labels);
        })
        .catch((error) => {
            console.error("Error fetching data:", error);
            // Handle error scenario (e.g., display an error message)
        });
};

document.addEventListener("DOMContentLoaded", () => {
    getChartData();
});
