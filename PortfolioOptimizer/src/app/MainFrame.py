"""Subclass of MainFrameBase, which is generated by wxFormBuilder."""

import wx
import wx.calendar as cal
import gui
import src.resources.finance as fin
import src.resources.utilities as u
import numpy as num
import scipy.interpolate.interpolate as interp
import matplotlib.dates as mdates
import matplotlib.backends.backend_wxagg as mpl
import time
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import matplotlib.pyplot as plt
from operator import itemgetter

# Implementing MainFrameBase
class MainFrame( gui.MainFrameBase ):
	def __init__( self, parent, portfolio ):
		gui.MainFrameBase.__init__( self, parent )
		self.portfolio = portfolio
		self.initPortGrid()
		
	# Handlers for MainFrameBase events.
	def initPortGrid(self):
		self.m_portfoliolist.InsertColumn(0,'')
		self.m_portfoliolist.InsertColumn(1, "Allocation")
		self.m_portfoliolist.InsertColumn(2, "Mean Rate")
		self.m_portfoliolist.InsertColumn(3, "Std. Deviation", width=120)
		self.m_portfoliolist.InsertColumn(4, "Correlation")
		self.m_portfoliolist.InsertColumn(5, "Beta")
		self.m_portfoliolist.InsertColumn(6, "Sharpe Ratio")
		self.m_portfoliolist.InsertStringItem(0, "Portfolio")
		self.m_portfoliolist.SetStringItem(0,1, str("%.2f" % 1.00))
		
	def startDateChanged( self, event ):
		# TODO: Implement startDateChanged
		pass
	
	def showEfficientFrontier(self, event):
		expReturn = []
		stdDeviation = []		
		for s in self.portfolio.optimizationResults:
			expReturn.append(s['ExpectedReturn'])
			weights = []
			for asset in self.portfolio.assets:
				weights.extend([r['Allocation'] for r in s['Results'] if r['Symbol'] == asset.symbol])
				
			w = num.array(weights)
			w2 = num.array(weights)
			matrix = self.portfolio.cvmatrix[0:len(w),0:len(w)]
			wvar = num.dot(w2.T, num.dot(matrix,w))
			wstd = num.sqrt(wvar)*num.sqrt(252)*100
			stdDeviation.append(wstd)
		
		sd = num.array(stdDeviation)
		er = num.array(expReturn)
		#xnew = num.linspace(sd.min(), sd.max(), 300)
		plt.figure(1)
		plt.subplot(111)
		plt.plot(stdDeviation, expReturn, "o-")
		#plt.Line2D(stdDeviation, expReturn)
		plt.xlabel('Standard Deviation (Risk)')
		plt.ylabel('Expected Rate of Return')
		plt.title('Efficient Frontier')
		plt.show()		
		
	def stockSelected( self, event ):
		sym = self.m_stocklist.GetItemText(event.m_itemIndex).encode('ascii')
		for s in self.portfolio.assets:
			if s.symbol == sym:
				stock = s
				break
		prices = [(date, price.adjclosing) for date,price in stock.prices.iteritems() if date >= self.portfolio.startdate]
		
		prices = sorted(prices, key=itemgetter(0), reverse=True)
		
		data = zip(*prices)
		
		plt.figure(1)
		plt.subplot(111)
		plt.plot_date(data[0], data[1], '-', xdate=True)
		plt.ylabel("Market Value")
		plt.title(stock.symbol)
		plt.show()
		
	def portfolioSelected(self, event):
		returns = []
		risks = []
		for asset in self.portfolio.assets:
			returns.append(asset.getMeanROR(annualized=True))
			risks.append(asset.getStd(annualized=True))
			
		plt.figure(1)
		plt.subplot(111)
		plt.scatter(returns, risks)
		plt.xlabel('Expected Rate of Return (Asset)')
		plt.ylabel('Standard Deviation (Risk)')
		plt.title('Portfolio Risk vs. Return')
		plt.show()
		
	def m_returnTypeChanged(self, event):
		method = self.m_returnType.GetStringSelection()
		if method != "Historical":
			method = "CAPM"
			self.m_expectedMarketrrLabel.Show()
			self.m_marketReturnRate.Show()
			self.SetSize((self.GetSize().width, self.GetSize().height+1))
			self.SetSize((self.GetSize().width, self.GetSize().height-1))
		else:
			self.m_expectedMarketrrLabel.Hide()
			self.m_marketReturnRate.Hide()
		self.portfolio.returnmethod = method
		#self.calculateGrid()
		
	def m_addButtonClick( self, event ):
		"""Parse the text in the input box"""
		stockstr = self.m_symbolinput.Value.encode('ascii')
		stocks = stockstr.split(",")
		stocks = [s.strip() for s in stocks]
		
		"""Get the historical prices and
		create a new Asset object for each stock symbol"""
		curSymbols = [a.symbol for a in self.portfolio.assets]
		for s in stocks:
			if s not in curSymbols:
				prices = u.getHistoricalPrices(s)
				asset = fin.Asset(s, prices)
				self.portfolio.addAsset(asset)
		self.m_symbolinput.SetValue("")
		self.updateGridSymbols()
				
	def updateGridSymbols(self):
		colcount = self.m_stocklist.ColumnCount
		if colcount < 1:
			self.m_stocklist.InsertColumn(0, "Symbol")
		for asset in self.portfolio.assets:
			pos = self.m_stocklist.FindItem(-1, asset.symbol)	
			if pos ==-1:
				pos = self.m_stocklist.ItemCount
				self.m_stocklist.InsertStringItem(pos, asset.symbol)
				self.m_stocklist.SetStringItem(pos,0, asset.symbol)
				
	def calculateGrid(self):
		
		colcount = self.m_stocklist.ColumnCount
		if colcount < 4:
			self.m_stocklist.InsertColumn(0, "Symbol")
			self.m_stocklist.InsertColumn(1, "Mean Rate")
			self.m_stocklist.InsertColumn(2, "Std. Deviation", width=120)
			self.m_stocklist.InsertColumn(3, "Allocation")
			self.m_stocklist.InsertColumn(4, "Correlation")
			self.m_stocklist.InsertColumn(5, "Beta")
			self.m_stocklist.InsertColumn(6, "Sharpe Ratio")
		
		if len(self.portfolio.assets) != 0:	
			MRAprices = u.getHistoricalPrices("SPY")
			marketRetAsset = fin.Asset("SPY", MRAprices)
			rfr = self.m_rfRadBox.GetStringSelection()
			
			rfRates = u.getHistoricalRates(rfr)
			mrRates = marketRetAsset.getRatesOfReturn(self.portfolio.startdate, self.portfolio.ratemethod)
			dates = u.date_range(self.portfolio.startdate)
			meanrates = []
			ratesmatrix = []
			sharpes = {}
			for asset in self.portfolio.assets:
				rates = asset.getRatesOfReturn(self.portfolio.startdate, self.portfolio.ratemethod)
				rateBundle = []
				for d in dates:
					if rfRates.has_key(d) and mrRates.has_key(d) and rates.has_key(d):
						rateBundle.append((rates[d],rfRates[d],mrRates[d]))
										
				asset.correlation = asset.getCorrelation(rateBundle)
				asset.beta = asset.getBeta(rateBundle, asset.correlation)
				asset.sharpe = asset.getSharpe(rateBundle)
				
				mostrecentrfr = max(rfRates.keys())
				if self.portfolio.returnmethod=="CAPM":	
					marketrr = float(self.m_marketReturnRate.Value)
					"""We are multiplying percentages by 100 (for displaying) but then we continue to use the standard deviations."""
					mean = asset.getMeanROR(rates, annualized=False, returnmethod="CAPM", marketrate=marketrr, rfrate=rfRates[mostrecentrfr], B=asset.beta)
				else:
					mean = asset.getMeanROR(rates, annualized=False, returnmethod="Historical")
				asset.rates =rates
				asset.mean = mean
				
				""" This will make annmeans a percentage of a percentage of annualized means?
					SHOULDN'T BE USING ANNUALIZED FOR OPTIMIZATION?"""
				"""annmeans.append(annmean/10000)"""
				meanrates.append(mean)
			
				sharpes[asset] = asset.sharpe
				
				ratesmatrix.append(rateBundle)
	
			
			self.portfolio.ratesmatrix = ratesmatrix
			cormatrix = self.portfolio.getMatrix(ratesmatrix)
			self.portfolio.cormatrix = cormatrix
			cvmatrix,stdmarket = self.portfolio.getMatrix(ratesmatrix, "covariance")
			self.portfolio.cvmatrix = cvmatrix
			self.portfolio.stdmarket = stdmarket
			self.portfolio.meanrates = meanrates
			
			if self.m_allocRads.GetSelection() == 1:
				#results = u.optimizePortfolio(self.portfolio, step=0.001)
				results = u.efficientFrontier(self.portfolio, step=0.0001)
				
				self.portfolio.optimizationResults = results
				
				e = min([res['ExpectedReturn'] for res in results])
				
				minrisk = 10000000
				optimalSolution = None
				for s in results:		
					tempweights = []
					for asset in self.portfolio.assets:
							tempweights.extend([w['Allocation'] for w in s['Results'] if w['Symbol'] == asset.symbol])
				
					tempwsharpe = 0
					i=0
					for asset in self.portfolio.assets:
						tempwsharpe += sharpes[asset]*tempweights[i]
						i=i+1
					print "Weighted Sharpe:"
					print tempwsharpe
					
					tempwcovwithmarket = self.portfolio.getWeightedCovariance(cvmatrix, tempweights, True)
					tempwvar = self.portfolio.getWeightedCovariance(cvmatrix, tempweights, False)
					""" getWeightedReturn annualizes the data. I think this means we end up annualizing it twice."""
					tempwrr = self.portfolio.getWeightedReturn(meanrates, tempweights)*100
					tempwcor = self.portfolio.getWeightedCorrelation(tempwcovwithmarket,tempwvar,stdmarket)
					tempwbeta = self.portfolio.getWeightedBeta(tempwcor, tempwvar,stdmarket)
					tempwstd = num.sqrt(tempwvar)*num.sqrt(252)*100
					if tempwstd<minrisk:
						i=0
						for asset in self.portfolio.assets:
							asset.weight =tempweights[i]
							i = i+1
						
						minrisk=tempwstd
						wrr = tempwrr
						wcor = tempwcor
						wbeta = tempwbeta
						wstd=tempwstd
						wsharpe=tempwsharpe
						
						
				self.m_EFbutton.Show()
				self.SetSize((self.GetSize().width, self.GetSize().height+1))
				self.SetSize((self.GetSize().width, self.GetSize().height-1))
			else:
				weights = [a.weight for a in reversed(self.portfolio.assets)]
				wsharpe = 0
				i=0
				for asset in self.portfolio.assets:
					wsharpe += sharpes[asset]*weights[i]
					i=i+1
				print "Weighted Sharpe:"
				print wsharpe
				covwithmarket = self.portfolio.getWeightedCovariance(cvmatrix, weights, True)
				wvar = self.portfolio.getWeightedCovariance(cvmatrix, weights, False)
				wrr = self.portfolio.getWeightedReturn(meanrates, weights)*100
				wcor = self.portfolio.getWeightedCorrelation(covwithmarket,wvar,stdmarket)
				wbeta = self.portfolio.getWeightedBeta(wcor, wvar,stdmarket)
				wstd = num.sqrt(wvar)*num.sqrt(252)*100
				self.m_EFbutton.Hide()
			
			#wrr = wsharpe*wstd
			"""
			print "Weighted annualized mean return rate?"
			print wrr
			print "Weight standard deviation:"
			print wstd
			"""
			
			for asset in self.portfolio.assets:
				pos = self.m_stocklist.FindItem(-1, asset.symbol)	
				"""We're for displaying! ANd only displaying!"""
				annmean = 100*252*asset.mean
				annstd = 100 * asset.getStd(asset.rates, annualized=True)
				if pos ==-1:
					pos = self.m_stocklist.ItemCount
					self.m_stocklist.InsertStringItem(pos, asset.symbol)
					self.m_stocklist.SetStringItem(0,1, str("%.2f" %  asset.weight))
					self.m_stocklist.SetStringItem(pos,2, str("%.2f" % annmean)+"%")
					self.m_stocklist.SetStringItem(pos,3, str("%.2f" % annstd)+"%")
					self.m_stocklist.SetStringItem(pos,4, str("%.2f" % asset.correlation))
					self.m_stocklist.SetStringItem(pos,5, str("%.2f" % asset.beta))
					self.m_stocklist.SetStringItem(pos,6, str("%.2f" % asset.sharpe))
				else:
					self.m_stocklist.SetStringItem(pos,1, str("%.2f" % asset.weight))
					self.m_stocklist.SetStringItem(pos,2, str("%.2f" % annmean)+"%")
					self.m_stocklist.SetStringItem(pos,3, str("%.2f" % annstd)+"%")
					self.m_stocklist.SetStringItem(pos,4, str("%.2f" % asset.correlation))
					self.m_stocklist.SetStringItem(pos,5, str("%.2f" % asset.beta))
					self.m_stocklist.SetStringItem(pos,6, str("%.2f" % asset.sharpe))
			
			self.m_portfoliolist.SetStringItem(0,1, str("%.2f" % 1.00))
			self.m_portfoliolist.SetStringItem(0,2, str("%.2f" % wrr)+"%")
			self.m_portfoliolist.SetStringItem(0,3, str("%.2f" % wstd)+"%")
			self.m_portfoliolist.SetStringItem(0,4, str("%.2f" % wcor))
			self.m_portfoliolist.SetStringItem(0,5, str("%.2f" % wbeta))
			self.m_portfoliolist.SetStringItem(0,6, str("%.2f" % wsharpe))
			
			assets = []
			assets.extend(self.portfolio.assets)
			assets.append(marketRetAsset)
			grid = self.m_corgrid
			grid.ClearGrid()
			while self.m_corgrid.NumberRows != 0:
				self.m_corgrid.DeleteCols()
				self.m_corgrid.DeleteRows()

			grid.AppendCols(len(assets))
			grid.AppendRows(len(assets))
			i = 0
			for asset in assets:
				self.m_corgrid.SetRowLabelValue(i, asset.symbol)
				self.m_corgrid.SetColLabelValue(i, asset.symbol)
				asset.covariances = {}
				i = i+1
							
			for i in range(len(assets)):
				for j in range(len(assets)):
					self.m_corgrid.SetCellValue(i, j, str("%.2f" % cormatrix[i][j]))
			
	def analyzeButtonClicked( self, event ):
		"""
		Set the start date of the portfolio based upon the
		stock with the most recent startdate
		"""
		
		dates = [stock.startdate for stock in self.portfolio.assets]
		
		dateWidgetValue = cal._wxdate2pydate(self.m_startingdate.GetValue())
		dates.append(dateWidgetValue)
		maxdate = max(dates)

		if not maxdate == dateWidgetValue:
			for stock in self.portfolio.assets:
				if stock.startdate == maxdate:
					datedictator = stock 
					message = "The stock %s has a later starting date than you specified. Your portfolio's start date will be set to %s ." %(datedictator.symbol, datedictator.startdate)			
					wx.MessageBox(message, 'Info', wx.OK | wx.ICON_INFORMATION)
				
			self.m_startingdate.SetValue(cal._pydate2wxdate(maxdate))
		self.portfolio.startdate = maxdate
		
		if self.m_meanCalcRadBox.GetStringSelection()=="Simple":
			self.portfolio.ratemethod = "Simple"
		else:
			self.portfolio.ratemethod = "Log"
		for asset in self.portfolio.assets:
			asset.rates = asset.getRatesOfReturn(self.portfolio.startdate, self.portfolio.ratemethod)
			
		if self.m_allocRads.GetSelection() == 0:
			self.weightDialog = WeightDialog(self, self.portfolio)
			self.weightDialog.Show()
		else:
			self.calculateGrid()

	def removeSelClicked( self, event ):
		sel = self.m_stocklist.GetFirstSelected()
		if not sel == -1:
			symbol = self.m_stocklist.GetItemText(sel)
			idx = 0
			for a in self.portfolio.assets:
				if a.symbol ==symbol:
					break
				idx = idx + 1
			del self.portfolio.assets[idx]
			self.m_stocklist.DeleteItem(sel)
			self.calculateGrid()
			
	def removeAllClicked( self, event ):
		del self.portfolio.assets
		self.portfolio.assets = []
		self.m_stocklist.DeleteAllItems()
		self.m_portfoliolist.DeleteAllItems()
		self.m_portfoliolist.DeleteAllColumns()
		self.initPortGrid()
		self.m_corgrid.ClearGrid()
		while self.m_corgrid.NumberRows != 0:
			self.m_corgrid.DeleteCols()
			self.m_corgrid.DeleteRows()
		self.calculateGrid()
		
	def rfrChanged( self, event ):
		pass
	
	def meanCalcMethChanged( self, event ):
		method = self.m_meanCalcRadBox.GetStringSelection()
		if method != "Simple":
			method = "Log"
		self.portfolio.ratemethod = method
		#self.calculateGrid()
	
	def m_mniExitClick( self, event ):
		# TODO: Implement m_mniExitClick
		pass

class WeightDialog( gui.WeightDialogBase ):
	def __init__( self, parent, portfolio ):
		gui.WeightDialogBase.__init__( self, parent )
		self.portfolio = portfolio
		self.totalValue = 100
		self.addSliders()
	
	def addSliders(self):
		self.sliders = {}
		self.sliderLabels = {}
		gSizer = self.sliderPanel.GetSizer()
		
		self.sliderPanel.DestroyChildren()
		val = 100/len(self.portfolio.assets)
		for asset in self.portfolio.assets:
			slider = wx.Slider(self.sliderPanel, wx.ID_ANY, val, 0, 100, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL|wx.SL_LABELS)
			label = wx.StaticText(self.sliderPanel, wx.ID_ANY, asset.symbol, wx.DefaultPosition, wx.DefaultSize, 0)
			label.SetFont( wx.Font( 12, 70, 90, 90, False, wx.EmptyString ) )
			slider.Bind( wx.EVT_SCROLL, self.sliderScrolling )
			gSizer.Add(label, 0, wx.ALL|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 5 )
			gSizer.Add(slider, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
			self.sliders[asset.symbol] = slider
			self.sliderLabels[asset.symbol] = label
		
		val *= len(self.portfolio.assets)
		if val != 100:
			add = 100-val
			sl = self.sliders.values()[0]
			sl.SetValue(sl.GetValue()+add)
			
		self.sliderPanel.SetSizer(gSizer)
		self.sliderPanel.Layout()
		self.sliderPanel.Fit()
		gSizer.Fit(self.sliderPanel)
		self.Layout()
		self.Fit()
	
	def sliderScrolling(self, event):
		slideObj = event.EventObject
		val = 0
		for s in self.sliders.itervalues():
			val += s.GetValue()
		
		if val > 100:
			surplus = val - 100
			while int(surplus) > 0:
				slides = [s for s in self.sliders.values() if s.GetId() != slideObj.GetId() and s.GetValue() != 0]
				diff = int(surplus/len(slides))
				if diff == 0:
					diff = surplus
					
				for s in slides:										
					sVal = s.GetValue()
					if sVal-diff >= 0:
						s.SetValue(int(sVal - diff))
						surplus -= int(diff)
					if surplus <= 0:
						break
			
	def weightCancelClicked( self, event ):
		self.Hide()
		self.Destroy()
	
	def weightOKClicked( self, event ):
		for asset in self.portfolio.assets:
			asset.weight = float(self.sliders[asset.symbol].GetValue())/100.0
		self.Hide()
		self.GetParent().calculateGrid()
		self.Destroy()
