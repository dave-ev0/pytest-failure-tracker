let testResults = {}; // Global variable to hold parsed JSON data

function handleFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];

    const reader = new FileReader();
    reader.onload = function(event) {
        const fileContent = event.target.result;
        try {
            testResults = JSON.parse(fileContent);
            renderChart();
        } catch (error) {
            console.error('Error parsing JSON file', error);
        }
    };
    reader.readAsText(file);
}

function renderChart() {
    const labels = Object.keys(testResults);
    const data = labels.map(key => {
        const test = testResults[key];
        return test.failures;
    });

    const ctx = document.getElementById('testResultsChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Failures',
                data: data,
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Failures'
                    }
                }
            }
        }
    });
}
