/*
 * SPDX-License-Identifier: Apache-2.0
 * 
 * IoT Intrusion Detection System - Audit Log Chaincode
 * Stores immutable detection verdicts on Hyperledger Fabric
 */

'use strict';

const { Contract } = require('fabric-contract-api');

class IDSAuditContract extends Contract {

    // Initialize ledger (called once when chaincode is deployed)
    async initLedger(ctx) {
        console.log('============= START : Initialize Ledger ===========');
        
        const initialRecords = [
            {
                deviceId: 'INIT_DEVICE',
                uid: 'INIT_UID',
                firmware: 'INIT_FW',
                verdict: 'SYSTEM_INIT',
                temperature: 0,
                humidity: 0,
                interval: 0,
                timestamp: Date.now()
            }
        ];

        for (let i = 0; i < initialRecords.length; i++) {
            initialRecords[i].docType = 'detectionRecord';
            await ctx.stub.putState('RECORD' + i, Buffer.from(JSON.stringify(initialRecords[i])));
            console.info('Added <--> ', initialRecords[i]);
        }
        
        console.log('============= END : Initialize Ledger ===========');
    }

    // Store a new detection verdict
    async storeVerdict(ctx, deviceId, uid, firmware, verdict, temperature, humidity, interval, timestamp) {
        console.log('============= START : Store Verdict ===========');

        const record = {
            docType: 'detectionRecord',
            deviceId: deviceId,
            uid: uid,
            firmware: firmware,
            verdict: verdict,
            temperature: parseFloat(temperature),
            humidity: parseFloat(humidity),
            interval: parseInt(interval),
            timestamp: parseInt(timestamp)
        };

        // Generate unique key using timestamp + deviceId
        const recordKey = `RECORD_${timestamp}_${deviceId}`;

        await ctx.stub.putState(recordKey, Buffer.from(JSON.stringify(record)));
        
        console.log(`✅ Stored verdict for device ${deviceId}: ${verdict}`);
        console.log('============= END : Store Verdict ===========');
        
        return JSON.stringify(record);
    }

    // Query a specific record by key
    async queryRecord(ctx, recordKey) {
        const recordAsBytes = await ctx.stub.getState(recordKey);
        
        if (!recordAsBytes || recordAsBytes.length === 0) {
            throw new Error(`${recordKey} does not exist`);
        }
        
        console.log(recordAsBytes.toString());
        return recordAsBytes.toString();
    }

    // Query all records for a specific device
    async queryRecordsByDevice(ctx, deviceId) {
        const queryString = {
            selector: {
                docType: 'detectionRecord',
                deviceId: deviceId
            }
        };

        const resultsIterator = await ctx.stub.getQueryResult(JSON.stringify(queryString));
        const results = await this._getAllResults(resultsIterator);
        
        return JSON.stringify(results);
    }

    // Query records by verdict type (TRUSTED, CLONE, ANOMALY, etc.)
    async queryRecordsByVerdict(ctx, verdict) {
        const queryString = {
            selector: {
                docType: 'detectionRecord',
                verdict: verdict
            }
        };

        const resultsIterator = await ctx.stub.getQueryResult(JSON.stringify(queryString));
        const results = await this._getAllResults(resultsIterator);
        
        return JSON.stringify(results);
    }

    // Query records within a time range
    async queryRecordsByTimeRange(ctx, startTime, endTime) {
        const queryString = {
            selector: {
                docType: 'detectionRecord',
                timestamp: {
                    $gte: parseInt(startTime),
                    $lte: parseInt(endTime)
                }
            }
        };

        const resultsIterator = await ctx.stub.getQueryResult(JSON.stringify(queryString));
        const results = await this._getAllResults(resultsIterator);
        
        return JSON.stringify(results);
    }

    // Get total count of records
    async getRecordCount(ctx) {
        const queryString = {
            selector: {
                docType: 'detectionRecord'
            }
        };

        const resultsIterator = await ctx.stub.getQueryResult(JSON.stringify(queryString));
        const results = await this._getAllResults(resultsIterator);
        
        return JSON.stringify({ count: results.length });
    }

    // Get records with ATTACK verdicts only
    async getAttackRecords(ctx) {
        const queryString = {
            selector: {
                docType: 'detectionRecord',
                verdict: {
                    $ne: 'TRUSTED'  // Not equal to TRUSTED
                }
            }
        };

        const resultsIterator = await ctx.stub.getQueryResult(JSON.stringify(queryString));
        const results = await this._getAllResults(resultsIterator);
        
        return JSON.stringify(results);
    }

    // Helper function to process query results
    async _getAllResults(iterator) {
        const allResults = [];
        let res = await iterator.next();
        
        while (!res.done) {
            if (res.value && res.value.value.toString()) {
                console.log(res.value.value.toString('utf8'));

                const Key = res.value.key;
                let Record;
                try {
                    Record = JSON.parse(res.value.value.toString('utf8'));
                } catch (err) {
                    console.log(err);
                    Record = res.value.value.toString('utf8');
                }
                allResults.push({ Key, Record });
            }
            res = await iterator.next();
        }
        await iterator.close();
        return allResults;
    }

    // Get blockchain transaction history for a specific record
    async getRecordHistory(ctx, recordKey) {
        const resultsIterator = await ctx.stub.getHistoryForKey(recordKey);
        const results = await this._getAllResults(resultsIterator);
        
        return JSON.stringify(results);
    }
}

module.exports = IDSAuditContract;