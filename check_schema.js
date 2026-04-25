require('dotenv').config();
const axios = require('axios');

async function checkSchema() {
    try {
        console.log("Fetching Airtable schema...");
        const response = await axios.get(
            `https://api.airtable.com/v0/meta/bases/${process.env.AIRTABLE_BASE_ID}/tables`,
            {
                headers: {
                    Authorization: `Bearer ${process.env.AIRTABLE_API_KEY}`
                }
            }
        );
        const table = response.data.tables.find(t => t.id === process.env.AIRTABLE_TABLE_NAME || t.name === process.env.AIRTABLE_TABLE_NAME);
        if (table) {
            console.log("✅ Your actual Airtable column names are (Case-Sensitive):");
            table.fields.forEach(f => console.log(` - "${f.name}" (${f.type})`));
        } else {
            console.log("❌ Table not found in metadata.");
        }
    } catch (error) {
        console.error("Failed to fetch schema via meta API:", error.response?.data?.error || error.message);
        
        console.log("Attempting fallback: reading existing records...");
        try {
            const getUrl = `https://api.airtable.com/v0/${process.env.AIRTABLE_BASE_ID}/${process.env.AIRTABLE_TABLE_NAME}?maxRecords=1`;
            const res2 = await axios.get(getUrl, {
                headers: { Authorization: `Bearer ${process.env.AIRTABLE_API_KEY}` }
            });
            if (res2.data.records.length > 0) {
                 console.log("✅ Extracted columns from the first record:");
                 console.log(Object.keys(res2.data.records[0].fields).map(k => ` - "${k}"`).join("\n"));
            } else {
                 console.log("❌ Table is empty, cannot guess fields.");
            }
        } catch (e) {
             console.log("Fallback failed.", e.message);
        }
    }
}

checkSchema();
