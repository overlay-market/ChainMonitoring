const mongoose = require("mongoose");

const liquiditySchema = new mongoose.Schema({
  market: {
    type: String,
    required: true,
  },
  currentLiquidity: {
    type: Number,
    required: true,
  },
});

// connect liquiditySchema with the "liquidities" collection
module.exports = mongoose.model("liquidity", liquiditySchema);
