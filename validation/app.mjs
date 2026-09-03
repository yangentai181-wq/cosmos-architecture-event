import {
  calculateCommuterDemand,
  calculateFinance,
  calculateResidentDemand,
  calculateSensitivity,
  requiredMonthlyRentPerRoom,
} from "./model.mjs";

const scenarios = {
  upper168: {
    constructionCost: 1_154_100_000,
    roomCount: 168,
    targetDomesticBeds: 84,
  },
  dorm91: {
    constructionCost: 974_100_000,
    roomCount: 91,
    targetDomesticBeds: 46,
  },
  unit84: {
    constructionCost: 974_100_000,
    roomCount: 84,
    targetDomesticBeds: 42,
  },
  apartment99: {
    constructionCost: 1_136_100_000,
    roomCount: 99,
    targetDomesticBeds: 50,
  },
};

const yen = new Intl.NumberFormat("ja-JP", {
  style: "currency",
  currency: "JPY",
  maximumFractionDigits: 0,
});
const integer = new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 0 });
const oneDecimal = new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 1 });

const element = (id) => document.getElementById(id);
const number = (id) => Number(element(id).value);
const rate = (id) => number(id) / 100;

function setStatus(id, message, warning = false) {
  const target = element(id);
  target.textContent = message;
  target.dataset.state = warning ? "warning" : "ok";
}

function updateResident() {
  try {
    const result = calculateResidentDemand({
      awayPrivateHumanities: number("resident-away-base"),
      studyYears: number("resident-study-years"),
      serviceableShare: rate("resident-serviceable"),
      awarenessRate: rate("resident-awareness"),
      qualifiedInterestRate: rate("resident-qualified"),
      applicationRate: rate("resident-application"),
      paidConversionRate: rate("resident-paid"),
      targetDomesticBeds: number("resident-target"),
    });
    element("resident-annual").textContent = `${integer.format(result.annualMarket)}人／年`;
    element("resident-serviceable-output").textContent = `${integer.format(result.serviceableAnnualMarket)}人／年`;
    element("resident-paid-output").textContent = `${oneDecimal.format(result.paidReservations)}人`;
    element("resident-coverage").textContent = `${result.coverageRatio.toFixed(2)}倍`;
    const enough = result.coverageRatio >= 1;
    setStatus(
      "resident-status",
      enough
        ? "仮定上は国内学生枠を充足。ただし、予約金を伴う実測値へ置き換えるまで確定しない。"
        : "仮定上は国内学生枠が不足。室数を減らすか、商圏・認知・転換率を見直す必要がある。",
      !enough,
    );
  } catch (error) {
    setStatus("resident-status", `入力エラー: ${error.message}`, true);
  }
}

function updateCommuter() {
  try {
    const result = calculateCommuterDemand({
      homePrivateHumanities: number("commuter-home-base"),
      serviceableShare: rate("commuter-serviceable"),
      awarenessRate: rate("commuter-awareness"),
      firstPaidRate: rate("commuter-first-paid"),
      repeatRate: rate("commuter-repeat"),
    });
    element("commuter-serviceable-output").textContent = `${integer.format(result.serviceableMarket)}人`;
    element("commuter-first-output").textContent = `${oneDecimal.format(result.firstPaidParticipants)}人`;
    element("commuter-repeat-output").textContent = `${oneDecimal.format(result.repeatParticipants)}人`;
    setStatus(
      "commuter-status",
      "反復参加者を運営容量と照合する。初回参加者数だけで共用部を拡大しない。",
      false,
    );
  } catch (error) {
    setStatus("commuter-status", `入力エラー: ${error.message}`, true);
  }
}

function financeInputs() {
  return {
    constructionCost: number("finance-construction"),
    landCost: number("finance-land"),
    roomCount: number("finance-rooms"),
    occupancyRate: rate("finance-occupancy"),
    managementRate: rate("finance-management"),
    monthlyFixedOperationCost: number("finance-operation"),
    structureLifeYears: 50,
    repairReserveDivisor: 2,
    annualAncillaryProfit: number("finance-ancillary"),
  };
}

function renderSensitivity(inputs) {
  const rows = calculateSensitivity({
    rents: [100_000, 125_000, 150_000, 160_000],
    occupancies: [0.9, 0.95, 1],
    financeInputs: inputs,
  });
  element("sensitivity-body").replaceChildren(
    ...rows.map((row) => {
      const tr = document.createElement("tr");
      const values = [
        yen.format(row.rent),
        `${(row.occupancyRate * 100).toFixed(0)}%`,
        yen.format(row.annualProfit),
        `${(row.totalInvestmentYield * 100).toFixed(2)}%`,
        row.totalInvestmentPaybackYears === null
          ? "回収不能"
          : `${row.totalInvestmentPaybackYears.toFixed(1)}年`,
      ];
      values.forEach((value) => {
        const td = document.createElement("td");
        td.textContent = value;
        tr.append(td);
      });
      return tr;
    }),
  );
}

function updateFinance() {
  try {
    const inputs = financeInputs();
    const targetYield = rate("finance-target-yield");
    const monthlyRent = number("finance-rent");
    const result = calculateFinance({
      ...inputs,
      monthlyRentPerRoom: monthlyRent,
    });
    const requiredRent = requiredMonthlyRentPerRoom({ ...inputs, targetYield });
    element("finance-profit").textContent = yen.format(result.annualProfit);
    element("finance-construction-yield").textContent = `${(result.constructionOnlyYield * 100).toFixed(2)}%`;
    element("finance-total-yield").textContent = `${(result.totalInvestmentYield * 100).toFixed(2)}%`;
    element("finance-payback").textContent = result.totalInvestmentPaybackYears === null
      ? "回収不能"
      : `${result.totalInvestmentPaybackYears.toFixed(1)}年`;
    element("finance-required-rent").textContent = `${yen.format(requiredRent)}／月`;
    element("finance-required-per-person").textContent = `${yen.format(requiredRent - monthlyRent)}／月`;
    const meetsTarget = result.totalInvestmentYield >= targetYield;
    setStatus(
      "finance-status",
      meetsTarget
        ? "土地代込みで目標利回りを満たす。次に、表示価格で予約金が集まるかを確認する。"
        : "土地代込みでは目標未達。賃料、戸数、建設費、土地条件、運営費のいずれかを変える必要がある。",
      !meetsTarget,
    );
    renderSensitivity(inputs);
  } catch (error) {
    setStatus("finance-status", `入力エラー: ${error.message}`, true);
  }
}

function applyScenario() {
  const scenario = scenarios[element("finance-scenario").value];
  element("finance-construction").value = scenario.constructionCost;
  element("finance-rooms").value = scenario.roomCount;
  element("resident-target").value = scenario.targetDomesticBeds;
  updateResident();
  updateFinance();
}

document.querySelectorAll("input").forEach((input) => {
  input.addEventListener("input", () => {
    updateResident();
    updateCommuter();
    updateFinance();
  });
});
element("finance-scenario").addEventListener("change", applyScenario);

updateResident();
updateCommuter();
updateFinance();
