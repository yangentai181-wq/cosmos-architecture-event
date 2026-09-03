function requireNonNegative(name, value) {
  if (!Number.isFinite(value) || value < 0) {
    throw new RangeError(`${name} must be a non-negative finite number`);
  }
}

function requirePositive(name, value) {
  if (!Number.isFinite(value) || value <= 0) {
    throw new RangeError(`${name} must be greater than 0`);
  }
}

function requireRate(name, value, { allowZero = true } = {}) {
  const lowerBoundIsValid = allowZero ? value >= 0 : value > 0;
  if (!Number.isFinite(value) || !lowerBoundIsValid || value > 1) {
    const range = allowZero ? "between 0 and 1" : "greater than 0 and at most 1";
    throw new RangeError(`${name} must be ${range}`);
  }
}

export function calculateResidentDemand({
  awayPrivateHumanities = 50_928,
  studyYears = 4,
  serviceableShare = 0.5,
  awarenessRate = 0.3,
  qualifiedInterestRate = 0.25,
  applicationRate = 0.4,
  paidConversionRate = 0.8,
  targetDomesticBeds = 84,
} = {}) {
  requireNonNegative("awayPrivateHumanities", awayPrivateHumanities);
  requirePositive("studyYears", studyYears);
  requireRate("serviceableShare", serviceableShare);
  requireRate("awarenessRate", awarenessRate);
  requireRate("qualifiedInterestRate", qualifiedInterestRate);
  requireRate("applicationRate", applicationRate);
  requireRate("paidConversionRate", paidConversionRate);
  requirePositive("targetDomesticBeds", targetDomesticBeds);

  const annualMarket = awayPrivateHumanities / studyYears;
  const serviceableAnnualMarket = annualMarket * serviceableShare;
  const awareStudents = serviceableAnnualMarket * awarenessRate;
  const qualifiedStudents = awareStudents * qualifiedInterestRate;
  const applications = qualifiedStudents * applicationRate;
  const paidReservations = Number((applications * paidConversionRate).toFixed(12));

  return {
    annualMarket,
    serviceableAnnualMarket,
    awareStudents,
    qualifiedStudents,
    applications,
    paidReservations,
    coverageRatio: paidReservations / targetDomesticBeds,
  };
}

export function calculateCommuterDemand({
  homePrivateHumanities = 120_337,
  serviceableShare = 0.4,
  awarenessRate = 0.05,
  firstPaidRate = 0.1,
  repeatRate = 0.3,
} = {}) {
  requireNonNegative("homePrivateHumanities", homePrivateHumanities);
  requireRate("serviceableShare", serviceableShare);
  requireRate("awarenessRate", awarenessRate);
  requireRate("firstPaidRate", firstPaidRate);
  requireRate("repeatRate", repeatRate);

  const serviceableMarket = homePrivateHumanities * serviceableShare;
  const awareStudents = serviceableMarket * awarenessRate;
  const firstPaidParticipants = awareStudents * firstPaidRate;
  const repeatParticipants = firstPaidParticipants * repeatRate;

  return {
    serviceableMarket,
    awareStudents,
    firstPaidParticipants,
    repeatParticipants,
  };
}

function validatedFinanceInputs({
  constructionCost = 1_154_100_000,
  landCost = 700_000_000,
  roomCount = 168,
  occupancyRate = 0.95,
  managementRate = 0.1,
  monthlyFixedOperationCost = 3_000_000,
  structureLifeYears = 50,
  repairReserveDivisor = 2,
  annualAncillaryProfit = 0,
} = {}) {
  requireNonNegative("constructionCost", constructionCost);
  requireNonNegative("landCost", landCost);
  requirePositive("roomCount", roomCount);
  requireRate("occupancyRate", occupancyRate, { allowZero: false });
  requireRate("managementRate", managementRate);
  if (managementRate === 1) {
    throw new RangeError("managementRate must be less than 1");
  }
  requireNonNegative("monthlyFixedOperationCost", monthlyFixedOperationCost);
  requirePositive("structureLifeYears", structureLifeYears);
  requirePositive("repairReserveDivisor", repairReserveDivisor);
  requireNonNegative("annualAncillaryProfit", annualAncillaryProfit);

  return {
    constructionCost,
    landCost,
    roomCount,
    occupancyRate,
    managementRate,
    monthlyFixedOperationCost,
    structureLifeYears,
    repairReserveDivisor,
    annualAncillaryProfit,
  };
}

export function calculateFinance({ monthlyRentPerRoom = 100_000, ...rawInputs } = {}) {
  requireNonNegative("monthlyRentPerRoom", monthlyRentPerRoom);
  const inputs = validatedFinanceInputs(rawInputs);
  const totalInvestment = inputs.constructionCost + inputs.landCost;
  const potentialAnnualRent = monthlyRentPerRoom * inputs.roomCount * 12;
  const effectiveAnnualRent = potentialAnnualRent * inputs.occupancyRate;
  const annualManagementCost = effectiveAnnualRent * inputs.managementRate;
  const annualFixedOperationCost = inputs.monthlyFixedOperationCost * 12;
  const annualRepairReserve =
    inputs.constructionCost / inputs.structureLifeYears / inputs.repairReserveDivisor;
  const annualProfit =
    effectiveAnnualRent -
    annualManagementCost -
    annualFixedOperationCost -
    annualRepairReserve +
    inputs.annualAncillaryProfit;

  return {
    totalInvestment,
    potentialAnnualRent,
    effectiveAnnualRent,
    annualManagementCost,
    annualFixedOperationCost,
    annualRepairReserve,
    annualProfit,
    constructionOnlyYield:
      inputs.constructionCost === 0 ? null : annualProfit / inputs.constructionCost,
    totalInvestmentYield: totalInvestment === 0 ? null : annualProfit / totalInvestment,
    totalInvestmentPaybackYears: annualProfit <= 0 ? null : totalInvestment / annualProfit,
  };
}

export function requiredMonthlyRentPerRoom({ targetYield = 0.07, ...rawInputs } = {}) {
  requireRate("targetYield", targetYield, { allowZero: false });
  const inputs = validatedFinanceInputs(rawInputs);
  const totalInvestment = inputs.constructionCost + inputs.landCost;
  const annualRepairReserve =
    inputs.constructionCost / inputs.structureLifeYears / inputs.repairReserveDivisor;
  const annualFixedOperationCost = inputs.monthlyFixedOperationCost * 12;
  const requiredEffectiveRentBeforeManagement =
    (totalInvestment * targetYield +
      annualFixedOperationCost +
      annualRepairReserve -
      inputs.annualAncillaryProfit) /
    (1 - inputs.managementRate);

  return (
    requiredEffectiveRentBeforeManagement /
    (inputs.roomCount * inputs.occupancyRate * 12)
  );
}

export function calculateSensitivity({
  rents = [100_000, 125_000, 150_000, 160_000],
  occupancies = [0.9, 0.95, 1],
  financeInputs = {},
} = {}) {
  if (!Array.isArray(rents) || !Array.isArray(occupancies)) {
    throw new TypeError("rents and occupancies must be arrays");
  }
  return rents.flatMap((rent) =>
    occupancies.map((occupancyRate) => ({
      rent,
      occupancyRate,
      ...calculateFinance({
        ...financeInputs,
        monthlyRentPerRoom: rent,
        occupancyRate,
      }),
    })),
  );
}
