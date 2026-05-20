const API = "http://127.0.0.1:8000";
let liquidityChart = null;

function getDays(){ return document.getElementById("days").value || 14; }
function getStress(){ return document.getElementById("stress").value || "normal"; }

async function api(path, options={}){
  const res = await fetch(API + path, {headers: {"Content-Type": "application/json"}, ...options});
  return await res.json();
}

async function trainML(){
  const result = await api("/train-ml");
  mlStatus.innerText = result.ml_status;
  alert("ML status: " + result.ml_status);
}

async function addAccount(){
  const data = {
    bank_name: bankName.value,
    account_name: accountName.value,
    currency: currency.value,
    balance: Number(balance.value),
    minimum_limit: Number(minimumLimit.value)
  };
  await api("/accounts", {method:"POST", body:JSON.stringify(data)});
  bankName.value = accountName.value = balance.value = minimumLimit.value = "";
  refreshAll();
}

async function addTransaction(){
  const data = {
    account_id: Number(accountSelect.value),
    amount: Number(amount.value),
    direction: direction.value,
    payment_system: paymentSystem.value,
    planned_date: plannedDate.value,
    description: description.value
  };
  await api("/transactions", {method:"POST", body:JSON.stringify(data)});
  amount.value = description.value = "";
  refreshAll();
}

async function loadAccounts(){
  const data = await api("/accounts");
  kpiAccounts.innerText = data.length;
  accountSelect.innerHTML = "";
  data.forEach(a => accountSelect.innerHTML += `<option value="${a.id}">${a.bank_name} / ${a.account_name} / ${a.currency}</option>`);
  accounts.innerHTML = "";
  data.forEach(a=>{
    accounts.innerHTML += `<div class="card"><h3>${a.bank_name} — ${a.account_name}</h3><p>${a.currency}</p><p>Balance: ${Number(a.balance).toLocaleString()}</p><p>Minimum: ${Number(a.minimum_limit).toLocaleString()}</p><button onclick="deleteAccount(${a.id})">Delete</button></div>`;
  });
}

async function deleteAccount(id){
  await api(`/accounts/${id}`, {method:"DELETE"});
  refreshAll();
}

async function loadTransactions(){
  const data = await api("/transactions");
  kpiTransactions.innerText = data.length;
  transactions.innerHTML = "<table><tr><th>ID</th><th>Account</th><th>Type</th><th>System</th><th>Amount</th><th>Date</th><th>Action</th></tr>" +
    data.map(t=>`<tr><td>${t.id}</td><td>${t.account_id}</td><td class="${t.direction==='OUTFLOW'?'bad':'good'}">${t.direction}</td><td>${t.payment_system}</td><td>${Number(t.amount).toLocaleString()}</td><td>${t.planned_date}</td><td><button onclick="deleteTransaction(${t.id})">Delete</button></td></tr>`).join("") + "</table>";
}

async function deleteTransaction(id){
  await api(`/transactions/${id}`, {method:"DELETE"});
  refreshAll();
}

async function loadAlerts(){
  const data = await api(`/alerts/ml?days=${getDays()}&stress=${getStress()}`);
  kpiAlerts.innerText = data.length;
  alerts.innerHTML = "";
  if(data.length === 0){
    alerts.innerHTML = `<div class="card"><h3 class="good">No ML liquidity risk</h3><p>ML forecast does not detect cash gap.</p></div>`;
    return;
  }
  data.forEach(a=>{
    alerts.innerHTML += `<div class="card risk"><h3>Risk: ${a.bank_name} / ${a.account_name}</h3><p>Date: ${a.date}</p><p>ML predicted balance: ${Number(a.predicted_balance).toLocaleString()} ${a.currency}</p><p>Minimum: ${Number(a.minimum_limit).toLocaleString()} ${a.currency}</p><p>Deficit: <b>${Number(a.deficit).toLocaleString()} ${a.currency}</b></p><p>Risk score: <b>${a.risk_score}%</b></p><p><b>Recommendation:</b> ${a.recommendation}</p></div>`;
  });
}

async function loadForecastChart(){
  const data = await api(`/forecast/ml?days=${getDays()}&stress=${getStress()}`);
  if(data.length > 0) mlStatus.innerText = data[0].ml_status || "trained";
  const datasets = [];
  let labels = [];
  data.forEach(item=>{
    labels = item.timeline.map(x=>x.date);
    datasets.push({label:`${item.bank_name} / ${item.account_name} (${item.currency})`, data:item.timeline.map(x=>x.predicted_balance), tension:.35});
  });
  if(liquidityChart) liquidityChart.destroy();
  liquidityChart = new Chart(document.getElementById("chart"), {
    type:"line",
    data:{labels,datasets},
    options:{
      responsive:true,
      plugins:{legend:{labels:{color:"#eef5ff"}}},
      scales:{
        x:{ticks:{color:"#b7c7dc"},grid:{color:"#1e3a5f"}},
        y:{ticks:{color:"#b7c7dc"},grid:{color:"#1e3a5f"}}
      }
    }
  });
}

async function refreshAll(){
  await loadAccounts();
  await loadTransactions();
  await loadAlerts();
  await loadForecastChart();
}
refreshAll();
