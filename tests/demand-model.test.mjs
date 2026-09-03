import assert from "node:assert/strict";
import test from "node:test";

import {
  calculateCommuterDemand,
  calculateFinance,
  calculateResidentDemand,
  calculateSensitivity,
  requiredMonthlyRentPerRoom,
} from "../validation/model.mjs";


test("defaults use the current five-floor 168-room upper-bound scenario", () => {
  const resident = calculateResidentDemand();
  const finance = calculateFinance();

  assert.ok(Math.abs(resident.coverageRatio - 1.8188571428571427) < 1e-12);
  assert.equal(finance.totalInvestment, 1_854_100_000);
  assert.equal(finance.annualProfit, 124_827_000);
});


test("resident funnel turns the public market base into paid reservations", () => {
  const result = calculateResidentDemand({
    awayPrivateHumanities: 50_928,
    studyYears: 4,
    serviceableShare: 0.5,
    awarenessRate: 0.3,
    qualifiedInterestRate: 0.25,
    applicationRate: 0.4,
    paidConversionRate: 0.8,
    targetDomesticBeds: 112,
  });

  assert.equal(result.annualMarket, 12_732);
  assert.equal(result.serviceableAnnualMarket, 6_366);
  assert.equal(result.paidReservations, 152.784);
  assert.ok(Math.abs(result.coverageRatio - 1.3641428571428572) < 1e-12);
});


test("commuter funnel keeps first purchase and repeat participation separate", () => {
  const result = calculateCommuterDemand({
    homePrivateHumanities: 120_337,
    serviceableShare: 0.4,
    awarenessRate: 0.05,
    firstPaidRate: 0.1,
    repeatRate: 0.3,
  });

  assert.ok(Math.abs(result.serviceableMarket - 48_134.8) < 1e-9);
  assert.ok(Math.abs(result.firstPaidParticipants - 240.674) < 1e-9);
  assert.ok(Math.abs(result.repeatParticipants - 72.2022) < 1e-9);
});


test("finance includes land, vacancy, management, fixed operation and repair reserve", () => {
  const result = calculateFinance({
    constructionCost: 1_213_600_000,
    landCost: 700_000_000,
    roomCount: 112,
    monthlyRentPerRoom: 100_000,
    occupancyRate: 0.95,
    managementRate: 0.1,
    monthlyFixedOperationCost: 3_000_000,
    structureLifeYears: 50,
    repairReserveDivisor: 2,
    annualAncillaryProfit: 0,
  });

  assert.equal(result.totalInvestment, 1_913_600_000);
  assert.equal(result.effectiveAnnualRent, 127_680_000);
  assert.equal(result.annualManagementCost, 12_768_000);
  assert.equal(result.annualRepairReserve, 12_136_000);
  assert.equal(result.annualProfit, 66_776_000);
  assert.ok(Math.abs(result.totalInvestmentYield - 0.03489548494983278) < 1e-12);
  assert.ok(Math.abs(result.totalInvestmentPaybackYears - 28.65700251587397) < 1e-12);
});


test("required rent solves the seven-percent total-investment target", () => {
  const assumptions = {
    constructionCost: 1_213_600_000,
    landCost: 700_000_000,
    roomCount: 112,
    occupancyRate: 0.95,
    managementRate: 0.1,
    monthlyFixedOperationCost: 3_000_000,
    structureLifeYears: 50,
    repairReserveDivisor: 2,
    annualAncillaryProfit: 0,
  };

  const requiredRent = requiredMonthlyRentPerRoom({
    ...assumptions,
    targetYield: 0.07,
  });
  const result = calculateFinance({
    ...assumptions,
    monthlyRentPerRoom: requiredRent,
  });

  assert.ok(Math.abs(requiredRent - 158_458.64661654134) < 1e-6);
  assert.ok(Math.abs(result.totalInvestmentYield - 0.07) < 1e-12);
});


test("sensitivity rows recalculate the model for every rent and occupancy pair", () => {
  const rows = calculateSensitivity({
    rents: [100_000, 160_000],
    occupancies: [0.9, 1],
    financeInputs: {
      constructionCost: 1_213_600_000,
      landCost: 700_000_000,
      roomCount: 112,
      managementRate: 0.1,
      monthlyFixedOperationCost: 3_000_000,
      structureLifeYears: 50,
      repairReserveDivisor: 2,
      annualAncillaryProfit: 0,
    },
  });

  assert.deepEqual(
    rows.map(({ rent, occupancyRate }) => [rent, occupancyRate]),
    [
      [100_000, 0.9],
      [100_000, 1],
      [160_000, 0.9],
      [160_000, 1],
    ],
  );
  assert.ok(rows[0].totalInvestmentYield < rows[1].totalInvestmentYield);
  assert.ok(rows[1].totalInvestmentYield < rows[3].totalInvestmentYield);
});


test("invalid rates are rejected instead of producing misleading outputs", () => {
  assert.throws(
    () => calculateResidentDemand({ serviceableShare: 1.1 }),
    /serviceableShare must be between 0 and 1/,
  );
  assert.throws(
    () => calculateFinance({ occupancyRate: 0 }),
    /occupancyRate must be greater than 0 and at most 1/,
  );
});
