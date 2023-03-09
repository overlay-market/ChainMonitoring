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
const multiCallAbi = require("./Abi/multicall.json");

const {
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
} = require("./helper");

const fs = require("fs");

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

  console.log(count[0], count[1], count[2], count[3], count[4], "count");

  // position.create({
  //   market: market[i],
  //   date: getDateAndTime(),
  //   collateralInOVLBetween0and10: count[0],
  //   collateralInOVLBetween11and20: count[1],
  //   collateralInOVLBetween21and100: count[2],
  //   collateralInOVLBetween101and500: count[3],
  //   collateralInOVLBetween501and1000: count[4],
  // });
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

  const valueData = await multiCall.multiCall(inputs, inputs0);
  // console.log(inputs, inputs0);

  for (let w = 0; w < eventLog.length; w++) {
    const cost = Number(costData[w]);
    const value = Number(valueData[w]);

    console.log(value, cost);

    if (value > cost) {
      const profit = value - cost;
      totalProfit += profit;
    } else {
      const loss = cost - value;
      totalLoss += loss;
    }
  }

  // uPnL.create({
  //   market: market[i],
  //   date: getDateAndTime(),
  //   totalUnrealizedProfit: totalProfit / number,
  //   totalUnrealizedLoss: totalLoss / number,
  // });
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

  // transfer.create({
  //   market: market[i],
  //   date: getDateAndTime(),
  //   totalMintedOVLInMarket: totalMintedInMarket / number,
  //   totalBurntOVLInMarket: totalBurntInMarket / number,
  // });

  console.log(totalBurntInMarket, totalMintedInMarket);
}

/**
 * Listens to the build function event,
 * calculates the %CapOI bought in new position
 */

SOL_USDmarket.on("Build", async (sender, positionId, userOI) => {
  await read(SOL_USDmarket, sender, positionId, userOI, "SOL/USD");
});

APE_USDmarket.on("Build", async (sender, positionId, userOI) => {
  await read(APE_USDmarket, sender, positionId, userOI, "APE/USD");
});

AVAX_USDmarket.on("Build", async (sender, positionId, userOI) => {
  await read(AVAX_USDmarket, sender, positionId, userOI, "AVAX/USD");
});

MATIC_USDmarket.on("Build", async (sender, positionId, userOI) => {
  await read(MATIC_USDmarket, sender, positionId, userOI, "MATIC/USD");
});

WBTC_USDmarket.on("Build", async (sender, positionId, userOI) => {
  await read(WBTC_USDmarket, sender, positionId, userOI, "WBTC/USD");
});

LINK_USDmarket.on("Build", async (sender, positionId, userOI) => {
  await read(LINK_USDmarket, sender, positionId, userOI, "LINK/USD");
});

// runs every 30 seconds
setInterval(async function () {
  for (let i = 0; i < markets.length; i++) {
    const marketContract = getAddress(config.MARKETS[liveMarkets[i]], abi);

    const filter = marketContract.filters.Build();
    const eventLog = await marketContract.queryFilter(filter, 0);

    const inputs = [];
    const inputs0 = [];

    let abi00 = ["function cost(address market, address owner, uint256 id)"];
    let iface = new ethers.utils.Interface(abi00);

    for (let e = 0; e < eventLog.length; e++) {
      inputs.push(
        iface.encodeFunctionData("cost", [
          `${config.MARKETS[liveMarkets[i]]}`,
          `${eventLog[e].args[0]}`,
          `${eventLog[e].args[1]}`,
        ])
      );

      inputs0.push(stateContract.address);
    }

    const costData = await multiCall.multiCall(inputs0, inputs);

    // await getuPnLinMarket(liveMarkets, eventLog, i, costData);
    await getPositionsInMarkets(eventLog, liveMarkets, i, costData);
    await getTransfersInMarkets(liveMarkets, i);
  }
}, 40000);

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
