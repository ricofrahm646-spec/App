class StrategyFactory:
    @staticmethod
    def get_ict_logic():
        return """
        // ICT Liquidity Sweep Logic
        double high = iHigh(Symbol(), PERIOD_H1, 1);
        double low = iLow(Symbol(), PERIOD_H1, 1);
        if(Bid > high) OrderSend(Symbol(), OP_SELL, 0.1, Bid, 3, Bid+200*_Point, Bid-400*_Point);
        if(Ask < low) OrderSend(Symbol(), OP_BUY, 0.1, Ask, 3, Ask-200*_Point, Ask+400*_Point);
        """

    @staticmethod
    def get_smc_logic():
        return """
        // SMC Orderblock Logic
        // Simplified: Check for engulfing at key levels
        if(iClose(Symbol(),0,1) > iHigh(Symbol(),0,2)) OrderSend(Symbol(),OP_BUY,0.1,Ask,3,0,0);
        """

    @staticmethod
    def get_gold_scalper_logic():
        return """
        // Gold Scalping Logic (XAUUSD)
        double rsi = iRSI(Symbol(),0,14,PRICE_CLOSE,0);
        if(rsi < 25) OrderSend(Symbol(),OP_BUY,0.1,Ask,3,Ask-100*_Point,Ask+200*_Point);
        if(rsi > 75) OrderSend(Symbol(),OP_SELL,0.1,Bid,3,Bid+100*_Point,Bid-200*_Point);
        """
