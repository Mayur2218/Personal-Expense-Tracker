document.addEventListener("DOMContentLoaded", function() {
    // Bar Chart: Monthly Expenses
    var ctxBar = document.getElementById('barChart').getContext('2d');
    new Chart(ctxBar, {
        type: 'bar',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Expenses (₹)',
                data: [15000, 13050, 14000, 10450, 15600, 13550],
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true } }
        }
    });

    // Pie Chart: Expense Categories
    var ctxPie = document.getElementById('pieChart').getContext('2d');
    new Chart(ctxPie, {
        type: 'pie',
        data: {
            labels: ['Food', 'Transport', 'Bills', 'Entertainment', 'Others'],
            datasets: [{
                data: [2500, 3000, 2020, 2080, 4050],
                backgroundColor: ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff']
            }]
        },
        options: { responsive: true }
    });
});
