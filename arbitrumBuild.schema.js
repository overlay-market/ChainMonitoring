const mongoose = require("mongoose");

const arbitrumBuildSchema = new mongoose.Schema({
  market: {
    type: String,
    required: true,
  },
  date: {
    type: String,
    required: true,
  },
  capOI: {
    type: Number,
    required: true,
  },
  userOI: {
    type: Number,
    required: true,
  },
  sender: {
    type: String,
    required: true,
  },
  collateralInOVL: {
    type: Number,
    required: true,
  },
  percentageOfCapOiBought: {
    type: Number,
    required: true,
  },
});

// connect arbitrumBuildSchema with the "arbitrumbuilds" collection
module.exports = mongoose.model("arbitrumBuild", arbitrumBuildSchema);
