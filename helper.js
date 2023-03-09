const ethers = require("ethers");
const config = require("./config.json");
const builds = require("./build.schema");

const network = {
  name: "Arbitrum Goerli",
  chainId: 421613,
  _defaultProvider: (providers) =>
    new providers.JsonRpcProvider(`https://goerli-rollup.arbitrum.io/rpc`),
};

const provider = ethers.getDefaultProvider(network);

const liveMarkets = [
  "WBTC/USD",
  "LINK/USD",
  "SOL/USD",
  "APE/USD",
  "AVAX/USD",
  "MATIC/USD",
];

const SOL_USDmarket = getAddress(config.MARKETS["SOL/USD"], abi);
const APE_USDmarket = getAddress(config.MARKETS["APE/USD"], abi);

const WBTC_USDmarket = getAddress(config.MARKETS["WBTC/USD"], abi);
const LINK_USDmarket = getAddress(config.MARKETS["LINK/USD"], abi);

const AVAX_USDmarket = getAddress(config.MARKETS["AVAX/USD"], abi);
const MATIC_USDmarket = getAddress(config.MARKETS["MATIC/USD"], abi);

const multiCall = getAddress(config.MULTI_CALL_CONTRACT_ADDRESS, multiCallAbi);

const stateContract = getAddress(
  config.CORE_CONTRACTS.OVERLAY_V1_STATE_CONTRACT_ADDRESS,
  abi2
);
const tokenContract = getAddress(
  config.CORE_CONTRACTS.OVERLAY_V1_TOKEN_CONTRACT_ADDRESS,
  abi3
);

function getAddress(address, abii) {
  const contract = new ethers.Contract(address, abii, provider);

  return contract;
}

function getDateAndTime() {
  const currentdate = new Date();
  const datetime =
    "Last Sync: " +
    currentdate.getDate() +
    "/" +
    (currentdate.getMonth() + 1) +
    "/" +
    currentdate.getFullYear() +
    " @ " +
    currentdate.getHours() +
    ":" +
    currentdate.getMinutes() +
    ":" +
    currentdate.getSeconds();

  return datetime;
}

async function read(marketContract, sender, positionId, userOI, marketName) {
  const marketCapOi = await stateContract.capOi(marketContract.address);

  const collateral = await stateContract.cost(
    marketContract.address,
    sender,
    positionId
  );

  const capOI = marketCapOi.toString();
  const percentage = userOI * 100;
  const percentageOfCapOiBought = percentage / capOI;

  builds.create({
    market: marketName,
    date: getDateAndTime(),
    capOI: capOI / 1000000000000000000,
    userOI: userOI / 1000000000000000000,
    sender: sender,
    collateralInOVL: collateral / 1000000000000000000,
    percentageOfCapOiBought: percentageOfCapOiBought / 1000000000000000000,
  });
}

export const helper = {
  read,
  multiCall,
  getAddress,
  liveMarkets,
  stateContract,
  tokenContract,
  SOL_USDmarket,
  APE_USDmarket,
  WBTC_USDmarket,
  LINK_USDmarket,
  AVAX_USDmarket,
  getDateAndTime,
  MATIC_USDmarket,
};
