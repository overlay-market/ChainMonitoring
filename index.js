require("dotenv").config();

const ethers = require("ethers");
const express = require("express");
const mongoose = require("mongoose");
const config = require("./config.json");
const { createServer } = require("http");

const app = express();
const server = createServer(app);
const uPnL = require("./uPnL.schema");
const abi = require("./Abi/abi1.json");
const abi2 = require("./Abi/abi2.json");
const abi3 = require("./Abi/abi3.json");

const builds = require("./build.schema");
const position = require("./position.schema");
const transfer = require("./transfer.schema");
const mongoDBUrl = `${process.env.MONGO_DB_URL}`;
const multiCallAbi = require("./Abi/multiCall.json");

const network = {
  name: "Ethereum Mainnet",
  chainId: 1,
  _defaultProvider: (providers) =>
    new providers.JsonRpcProvider(
      `https://eth-mainnet.alchemyapi.io/v2/${process.env.ID}`
    ),
};

const number = 1000000000000000000;
const provider = ethers.getDefaultProvider(network);

const marketContract = new ethers.Contract(
  config.MARKETS["ETH/USDC"],
  abi,
  provider
);

const multiCall = new ethers.Contract(
  config.MULTI_CALL_CONTRACT_ADDRESS,
  multiCallAbi,
  provider
);

const stateContract = new ethers.Contract(
  config.CORE_CONTRACTS.OVERLAY_V1_STATE_CONTRACT_ADDRESS,
  abi2,
  provider
);
const tokenContract = new ethers.Contract(
  config.CORE_CONTRACTS.OVERLAY_V1_TOKEN_CONTRACT_ADDRESS,
  abi3,
  provider
);

/**
 * Returns the amount of OVL as collateral in different positions.
 */
async function getPositionsInMarkets(eventLog, market, i, costData) {
  const count = [0, 0, 0, 0, 0];

  for (let y = 0; y < eventLog.length; y++) {
    const collateral = Number(costData[y]) / number;
    if (collateral > 0 && collateral <= 10) {
      count[0] += 1;
    } else if (collateral > 10 && collateral <= 20) {
      count[1] += 1;
    } else if (collateral > 20 && collateral <= 100) {
      count[2] += 1;
    } else if (collateral > 100 && collateral <= 500) {
      count[3] += 1;
    } else if (collateral > 500 && collateral <= 1000) {
      count[4] += 1;
    }
  }

  position.create({
    market: market[i],
    date: getDateAndTime(),
    collateralInOVLBetween0and10: count[0],
    collateralInOVLBetween11and20: count[1],
    collateralInOVLBetween21and100: count[2],
    collateralInOVLBetween101and500: count[3],
    collateralInOVLBetween501and1000: count[4],
  });
}

/**
 * Returns the unrealized profit and loss of positions in a market.
 */
async function getuPnLinMarket(market, eventLog, i, costData) {
  let totalLoss = 0;
  let totalProfit = 0;

  const inputs = [];
  const inputs0 = [];

  let abi = ["function value(address market, address owner, uint256 id)"];
  let iface = new ethers.utils.Interface(abi);

  for (let z = 0; z < eventLog.length; z++) {
    inputs.push(stateContract.address);

    inputs0.push(
      iface.encodeFunctionData("value", [
        `${config.MARKETS[market[i]]}`,
        `${eventLog[z].args[0]}`,
        `${eventLog[z].args[1]}`,
      ])
    );
  }

  const valueData = await multiCall.mul(inputs, inputs0);

  for (let w = 0; w < eventLog.length; w++) {
    const cost = Number(costData[w]);
    const value = Number(valueData[w]);

    if (value > cost) {
      const profit = value - cost;
      totalProfit += profit;
    } else {
      const loss = cost - value;
      totalLoss += loss;
    }
  }

  uPnL.create({
    market: market[i],
    date: getDateAndTime(),
    totalUnrealizedProfit: totalProfit / number,
    totalUnrealizedLoss: totalLoss / number,
  });
}

/**
 * Returns the total minted and burnt OVL in a market.
 */
async function getTransfersInMarkets(market, i) {
  const filter1 = tokenContract.filters.Transfer(
    ethers.constants.AddressZero,
    config.MARKETS[market[i]]
  );
  const mintedEventLog = await tokenContract.queryFilter(filter1, 0);

  const filter2 = tokenContract.filters.Transfer(
    config.MARKETS[market[i]],
    ethers.constants.AddressZero
  );
  const burntEventLog = await tokenContract.queryFilter(filter2, 0);

  let totalBurntInMarket = 0;
  let totalMintedInMarket = 0;

  for (let r = 0; r < burntEventLog.length; r++) {
    totalBurntInMarket += Number(burntEventLog[r].args[2]);
  }

  for (let x = 0; x < mintedEventLog.length; x++) {
    totalMintedInMarket += Number(mintedEventLog[x].args[2]);
  }

  transfer.create({
    market: market[i],
    date: getDateAndTime(),
    totalMintedOVLInMarket: totalMintedInMarket / number,
    totalBurntOVLInMarket: totalBurntInMarket / number,
  });
}

/**
 * Listens to the build function event,
 * calculates the %CapOI bought in new position
 */
marketContract.on("Build", async (sender, positionId, userOI) => {
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
    market: "ETH/USDC",
    date: getDateAndTime(),
    capOI: capOI / number,
    userOI: userOI / number,
    sender: sender,
    collateralInOVL: collateral / 1000000000000000000,
    percentageOfCapOiBought: percentageOfCapOiBought / number,
  });
});

// runs every 30 seconds
setInterval(async function () {
  // Current markets on mainnet
  const markets = ["ETH/USDC"];

  for (let i = 0; i < markets.length; i++) {
    const marketContract = new ethers.Contract(
      config.MARKETS[markets[i]],
      abi,
      provider
    );

    const filter = marketContract.filters.Build();
    const eventLog = await marketContract.queryFilter(filter, 0);

    const inputs = [];
    const inputs0 = [];

    let abi00 = ["function cost(address market, address owner, uint256 id)"];
    let iface = new ethers.utils.Interface(abi00);

    for (let e = 0; e < eventLog.length; e++) {
      inputs.push(
        iface.encodeFunctionData("cost", [
          `${config.MARKETS[markets[i]]}`,
          `${eventLog[e].args[0]}`,
          `${eventLog[e].args[1]}`,
        ])
      );

      inputs0.push(stateContract.address);
    }

    const costData = await multiCall.mul(inputs0, inputs);

    await getuPnLinMarket(markets, eventLog, i, costData);
    await getPositionsInMarkets(eventLog, markets, i, costData);
    await getTransfersInMarkets(markets, i);
  }
}, 30000);

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

mongoose.connection.once("open", () => {
  console.log("connection ready");
});

mongoose.connection.on("error", (err) => {
  console.error(err);
});

server.listen(8080, async function () {
  await mongoose.connect(mongoDBUrl);
  console.log("Listening on http://0.0.0.0:8080");
});
