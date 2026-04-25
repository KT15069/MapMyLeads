require('dotenv').config();
const { scrapeGoogleMaps } = require('./scraper');
const airtable = require('./airtable');

async function main() {
    try {
        console.log("Scraping top 5 handicraft small scaled businesses in USA...");
        const newLeads = await scrapeGoogleMaps({
            query: "handicraft small scaled businesses",
            location: "USA",
            max_results: 5
        });

        console.log(`Found ${newLeads.length} leads.`);
        console.log(JSON.stringify(newLeads, null, 2));
        
        let savedRecords = [];
        if (newLeads.length > 0) {
            console.log("Saving new leads to Airtable...");
            savedRecords = await airtable.saveLeads(newLeads);
            console.log(`Successfully saved ${savedRecords.length} records.`);
        }
    } catch (error) {
        console.error("Error:", error.message);
    }
}

main();
