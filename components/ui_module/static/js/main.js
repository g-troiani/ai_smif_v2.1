// Initialize WebSocket connection
const socket = io();

// WebSocket event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    updateUIElements(); // Update UI elements on connection
});

socket.on('update', (data) => {
    // Update account balance
    if (data.balance) {
        const balanceElement = document.getElementById('account-balance');
        if (balanceElement) {
            balanceElement.textContent = `$${data.balance.toFixed(2)}`;
        }
    }
    
    // Update strategy performance
    if (data.performance) {
        const performanceElement = document.getElementById('strategy-performance');
        if (performanceElement) {
            performanceElement.textContent = `${data.performance.toFixed(2)}%`;
        }
    }

    // Update portfolio value
    if (data.portfolio_value) {
        const portfolioElement = document.getElementById('portfolio-value');
        if (portfolioElement) {
            portfolioElement.textContent = `$${data.portfolio_value.toFixed(2)}`;
        }
    }

    // Update strategy status
    if (data.strategy_status) {
        const statusElement = document.getElementById('strategy-status');
        if (statusElement) {
            statusElement.textContent = data.strategy_status;
            statusElement.className = `badge ${data.strategy_status === 'Active' ? 'badge-success' : 'badge-secondary'}`;
        }
    }
    
    // Update positions table
    if (data.positions) {
        updatePositionsTable(data.positions);
    }

    // Update open orders
    if (data.orders) {
        updateOrdersTable(data.orders);
    }
});

// Handle server alerts
socket.on('alert', (data) => {
    if (data.message) {
        alert(data.message);
    }
});

// Handle data stream status updates
socket.on('data_status', (data) => {
    const streamStatus = document.getElementById('stream-status');
    const lastUpdate = document.getElementById('last-update');
    
    if (streamStatus && data.status) {
        streamStatus.textContent = data.status;
        streamStatus.className = `badge badge-${data.status === 'Active' ? 'success' : 'secondary'}`;
    }
    
    if (lastUpdate && data.last_update) {
        lastUpdate.textContent = new Date(data.last_update).toLocaleString();
    }
});

// Setup DOM event listeners
document.addEventListener('DOMContentLoaded', () => {
    initializeUIElements();

    // Ticker form handling
    const tickerForm = document.getElementById('add-ticker-form');
    if (tickerForm) {
        tickerForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const ticker = document.getElementById('ticker-input').value.trim().toUpperCase();
            if (!ticker) {
                alert('Please enter a valid ticker symbol');
                return;
            }

            fetch('/api/add_ticker', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Ticker added successfully');
                    tickerForm.reset();
                    updateUIElements(); // Refresh UI after adding ticker
                } else {
                    alert(data.message || 'Error adding ticker');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error adding ticker');
            });
        });
    }

    // Ticker file upload handling
    const tickerUploadForm = document.getElementById('ticker-upload-form');
    if (tickerUploadForm) {
        tickerUploadForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const fileInput = document.getElementById('ticker-file');
            const file = fileInput.files[0];
            if (!file) {
                alert('Please select a file to upload');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            fetch('/api/upload_tickers', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Ticker list uploaded successfully');
                    tickerUploadForm.reset();
                    updateUIElements();
                } else {
                    alert(data.message || 'Error uploading ticker list');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error uploading ticker list');
            });
        });
    }

    // Data configuration form handling
    const dataConfigForm = document.getElementById('data-config-form');
    if (dataConfigForm) {
        dataConfigForm.addEventListener('submit', (event) => {
            event.preventDefault();
            
            const formData = new FormData(dataConfigForm);
            const interval = formData.get('data_interval');
            const period = formData.get('lookback_period');

            fetch('/api/load_historical_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ interval, period })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Data configuration updated successfully');
                    updateUIElements();
                } else {
                    alert(data.message || 'Error updating data configuration');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error updating data configuration');
            });
        });
    }

    // Strategy configuration form validation
    const strategyForm = document.getElementById('strategy-config-form');
    if (strategyForm) {
        strategyForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const ticker = document.getElementById('ticker').value.trim();
            if (!ticker) {
                alert('Please enter a valid ticker symbol');
                return;
            }
            strategyForm.submit();
        });
    }

    // Backtest configuration form validation
    const backtestForm = document.getElementById('backtest-config-form');
    if (backtestForm) {
        backtestForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            
            if (!startDate || !endDate) {
                alert('Please select both start and end dates');
                return;
            }
            if (new Date(startDate) >= new Date(endDate)) {
                alert('Start date must be before end date');
                return;
            }
            backtestForm.submit();
        });
    }

    // Manual buy button handling
    const buyButton = document.getElementById('buy-button');
    if (buyButton) {
        buyButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to execute a Buy order?')) {
                fetch('/api/manual_trade', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'buy' })
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message || 'Trade executed successfully');
                    updateUIElements();
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error executing trade');
                });
            }
        });
    }

    // Manual sell button handling
    const sellButton = document.getElementById('sell-button');
    if (sellButton) {
        sellButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to execute a Sell order?')) {
                fetch('/api/manual_trade', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'sell' })
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message || 'Trade executed successfully');
                    updateUIElements();
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error executing trade');
                });
            }
        });
    }

    // Panic button handling
    const panicButton = document.getElementById('panic-button');
    if (panicButton) {
        panicButton.addEventListener('click', () => {
            if (confirm('This will liquidate all positions. Proceed?')) {
                fetch('/api/liquidate_positions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message || 'Positions liquidated successfully');
                    updateUIElements();
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error liquidating positions');
                });
            }
        });
    }

    // Initialize refresh button
    initializeRefreshButton();
});

// Helper function to update positions table
function updatePositionsTable(positions) {
    const tableBody = document.getElementById('positions-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '';
    positions.forEach(position => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${position.ticker}</td>
            <td>${position.quantity}</td>
            <td>$${position.price.toFixed(2)}</td>
            <td>${position.pnl ? position.pnl.toFixed(2) + '%' : 'N/A'}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Helper function to update orders table
function updateOrdersTable(orders) {
    const tableBody = document.getElementById('orders-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '';
    orders.forEach(order => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${order.ticker}</td>
            <td>${order.type}</td>
            <td>${order.quantity}</td>
            <td>$${order.price.toFixed(2)}</td>
            <td>${order.status}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Initialize UI elements
function initializeUIElements() {
    // Account summary section
    const accountSummary = document.getElementById('account-summary');
    if (accountSummary) {
        accountSummary.innerHTML = `
            <div class="card mb-4">
                <div class="card-header">Account Summary</div>
                <div class="card-body">
                    <p>Balance: <span id="account-balance">$0.00</span></p>
                    <p>Portfolio Value: <span id="portfolio-value">$0.00</span></p>
                    <p>Performance: <span id="strategy-performance">0.00%</span></p>
                    <p>Strategy Status: <span id="strategy-status" class="badge badge-secondary">Inactive</span></p>
                </div>
            </div>
        `;
    }

    // Data status section
    const dataStatus = document.getElementById('data-status');
    if (dataStatus) {
        dataStatus.innerHTML = `
            <div class="card mb-4">
                <div class="card-header">Data Stream Status</div>
                <div class="card-body">
                    <p>Status: <span id="stream-status" class="badge badge-secondary">Inactive</span></p>
                    <p>Last Update: <span id="last-update">Never</span></p>
                </div>
            </div>
        `;
    }

    // Fetch initial data
    updateUIElements();
}

// Initialize refresh button
function initializeRefreshButton() {
    const refreshButton = document.getElementById('refresh-button');
    if (refreshButton) {
        refreshButton.addEventListener('click', () => {
            updateUIElements();
        });
    }
}

// Update UI elements with latest data
function updateUIElements() {
    fetch('/api/account/status')
        .then(response => response.json())
        .then(data => {
            if (data.balance) {
                document.getElementById('account-balance').textContent = `$${data.balance.toFixed(2)}`;
            }
            if (data.portfolio_value) {
                document.getElementById('portfolio-value').textContent = `$${data.portfolio_value.toFixed(2)}`;
            }
            if (data.performance) {
                document.getElementById('strategy-performance').textContent = `${data.performance.toFixed(2)}%`;
            }
            if (data.positions) {
                updatePositionsTable(data.positions);
            }
            if (data.orders) {
                updateOrdersTable(data.orders);
            }
        })
        .catch(error => {
            console.error('Error updating UI:', error);
        });
    // Update data status
    fetch('/api/data_status')
        .then(response => response.json())
        .then(data => {
            const lastUpdate = document.getElementById('last-update');
            if (lastUpdate && data.last_update) {
                lastUpdate.textContent = new Date(data.last_update).toLocaleString();
            }
        })
        .catch(error => {
            console.error('Error updating data status:', error);
        });
}


// Add to existing main.js file
socket.on('data_update', (data) => {
    const streamStatus = document.getElementById('stream-status');
    const lastUpdate = document.getElementById('last-update');
    
    if (streamStatus) {
        streamStatus.textContent = data.status;
        streamStatus.className = `badge badge-${data.status === 'Active' ? 'success' : 'secondary'}`;
    }
    
    if (lastUpdate && data.timestamp) {
        lastUpdate.textContent = new Date(data.timestamp).toLocaleString();
    }
});
