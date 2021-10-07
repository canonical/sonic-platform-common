from ...fields import consts
from ..xcvr_api import XcvrApi
import struct
import time

LPLPAGE = 0x9f
CDB_RPL_OFFSET = 136
CDB_WRITE_MSG_START = 130
PAGE_LENGTH = 128
INIT_OFFSET = 128
CMDLEN = 2
MAX_TRY = 3

class CmisCdbApi(XcvrApi):
    def __init__(self, xcvr_eeprom):
        super(CmisCdbApi, self).__init__(xcvr_eeprom)
    
    def cdb1_chkflags(self):
        '''
        This function detects if there is datapath or module firmware fault.
        If there is no firmware fault, it checks if CDB command completes.
        It retruns True if the CDB command is incomplete and returns False if complete

        Bit 7: L-Cdb2CommandComplete Latched Flag to indicate completion of the CDB command
        for CDB block 2. Support is advertised in field 01h:163.7-6

        Bit 6: L-Cdb1CommandComplete Latched Flag to indicate completion of the CDB command
        for CDB block 1. Support is advertised in field 01h:163.7-6

        Bit 5-3: - Reserved

        Bit 2: L-DataPathFirmwareFault Latched Flag to indicate that subordinated firmware in an
        auxiliary device for processing transmitted or received
        signals (e.g. a DSP) has failed.

        Bit 1: L-ModuleFirmwareFault Latched Flag to indicate that self-supervision of the main
        module firmware has detected a failure in the main module
        firmware itself. There are several possible causes of the
        error such as program memory becoming corrupted and
        incomplete firmware loading.

        Bit 0: L-ModuleStateChanged Latched Flag to indicate a Module State Change
        '''
        status = self.xcvr_eeprom.read(consts.MODULE_FIRMWARE_FAULT_INFO)
        datapath_firmware_fault = bool((status >> 2) & 0x1)
        module_firmware_fault = bool((status >> 1) & 0x1)
        cdb1_command_complete = bool((status >> 6) & 0x1)
        assert not datapath_firmware_fault
        assert not module_firmware_fault
        if cdb1_command_complete:
            return False
        else:
            return True
    
    def cdb_chkcode(self, cmd):
        '''
        This function calculates and returns the checksum of a CDB command
        '''
        checksum = 0
        for byte in cmd:
            checksum += byte   
        return 0xff - (checksum & 0xff)

    def cdb1_chkstatus(self):
        '''
        This function checks the CDB status.
        The format of returned values is busy flag, failed flag and cause

        CDB command status
        Bit 7: CdbIsBusy
        Bit 6: CdbHasFailed
        Bit 5-0: CdBCommandResult
        Coarse Status     CdbIsBusy       CdbHasFailed
        IN PROGRESS       1               X (dont care)
        SUCCESS           0               0
        FAILED            0               1

        IN PROGRESS
            00h=Reserved
            01h=Command is captured but not processed
            02h=Command checking is in progress
            03h=Previous CMD was ABORTED by CMD Abort
            04h-1Fh=Reserved
            20h-2Fh=Reserved
            30h-3Fh=Custom

        SUCCESS
            00h=Reserved
            01h=Command completed successfully
            02h=Reserved
            03h=Previous CMD was ABORTED by CMD Abort
            04h-1Fh=Reserved
            20h-2Fh=Reserved
            30h-3Fh=Custom

        FAILED
            00h=Reserved
            01h=CMDCode unknown
            02h=Parameter range error or parameter not supported
            03h=Previous CMD was not ABORTED by CMD Abort
            04h=Command checking time out
            05h=CdbCheckCode Error
            06h=Password related error (command specific meaning)
            07h=Command not compatible with operating status
            08h-0Fh=Reserved for STS command checking error
            10h-1Fh=Reserved
            20h-2Fh=For individual STS command or task error
            30h-3Fh=Custom
        '''
        status = self.xcvr_eeprom.read(consts.CDB1_STATUS)
        is_busy =  bool((status >> 7) & 0x1)
        while is_busy:
            time.sleep(1)
            is_busy =  bool((status >> 7) & 0x1)
        return status

    def write_cdb(self, cmd):
        '''
        This function writes a CDB command to page 0x9f
        '''
        self.xcvr_eeprom.write_flexible(LPLPAGE*PAGE_LENGTH+CDB_WRITE_MSG_START, len(cmd)-CMDLEN, cmd[CMDLEN:])
        self.xcvr_eeprom.write_flexible(LPLPAGE*PAGE_LENGTH+INIT_OFFSET, CMDLEN, cmd[:CMDLEN])

    def read_cdb(self):
        '''
        This function reads the reply of a CDB command from page 0x9f
        '''
        rpllen = self.xcvr_eeprom.read(consts.CDB_RPL_LENGTH)
        rpl_chkcode = self.xcvr_eeprom.read(consts.CDB_RPL_CHKCODE)
        rpl = self.xcvr_eeprom.read_flexible(LPLPAGE*PAGE_LENGTH+CDB_RPL_OFFSET, rpllen)
        return rpllen, rpl_chkcode, rpl

    # Query status
    def cmd0000h(self):
        cmd = bytearray(b'\x00\x00\x00\x00\x02\x00\x00\x00\x00\x10')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return self.read_cdb()

    # Enter password
    def cmd0001h(self):
        cmd = bytearray(b'\x00\x01\x00\x00\x04\x00\x00\x00\x00\x00\x10\x11')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return self.read_cdb()

    def cmd0040h(self):
        cmd = bytearray(b'\x00\x40\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return self.read_cdb()

    # Firmware Update Features Supported
    def cmd0041h(self):
        cmd = bytearray(b'\x00\x41\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return self.read_cdb()

    # Get FW info
    def cmd0100h(self):
        cmd = bytearray(b'\x01\x00\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return self.read_cdb()

    # Start FW download
    def cmd0101h(self, startLPLsize, header, imagesize):
        print("Image size is {}".format(imagesize))
        cmd = bytearray(b'\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        cmd[132-INIT_OFFSET] = startLPLsize + 8
        cmd[136-INIT_OFFSET] = (imagesize >> 24) & 0xff
        cmd[137-INIT_OFFSET] = (imagesize >> 16) & 0xff
        cmd[138-INIT_OFFSET] = (imagesize >> 8)  & 0xff
        cmd[139-INIT_OFFSET] = (imagesize >> 0)  & 0xff
        cmd += header
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return status

    # Abort FW download
    def cmd0102h(self):
        cmd = bytearray(b'\x01\x02\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return status

    # Download FW with LPL
    def cmd0103h(self, addr, data):
        # lpl_len includes 136-139, four bytes, data is 116-byte long. 
        lpl_len = len(data) + 4
        cmd = bytearray(b'\x01\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        cmd[132-INIT_OFFSET] = lpl_len & 0xff
        cmd[136-INIT_OFFSET] = (addr >> 24) & 0xff
        cmd[137-INIT_OFFSET] = (addr >> 16) & 0xff
        cmd[138-INIT_OFFSET] = (addr >> 8)  & 0xff
        cmd[139-INIT_OFFSET] = (addr >> 0)  & 0xff
        # pad data to 116 bytes just in case, make sure to fill all 0x9f page
        paddedPayload = data.ljust(116, b'\x00')
        cmd += paddedPayload
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return status

    #  Download FW with EPL
    def cmd0104h(self, addr, data, autopaging_flag, writelength):
        epl_len = 2048
        subtime = time.time()
        if not autopaging_flag:
            pages = epl_len // PAGE_LENGTH
            if (epl_len % PAGE_LENGTH) != 0:
                pages += 1
            # write to page 0xA0 - 0xAF (max of 16 pages)
            for pageoffset in range(pages):
                next_page = 0xa0 + pageoffset
                if PAGE_LENGTH*(pageoffset + 1) <= epl_len:
                    datachunk = data[PAGE_LENGTH*pageoffset : PAGE_LENGTH*(pageoffset + 1)]
                    self.xcvr_eeprom.write_flexible(next_page*PAGE_LENGTH+INIT_OFFSET, PAGE_LENGTH, datachunk)
                else:
                    datachunk = data[INIT_OFFSET*pageoffset : ]
                    self.xcvr_eeprom.write_flexible(next_page*PAGE_LENGTH+INIT_OFFSET, len(datachunk), datachunk)
        else:
            sections = epl_len // writelength
            if (epl_len % writelength) != 0:
                sections += 1
            # write to page 0xA0 - 0xAF (max of 16 pages), with length of writelength per piece
            for offset in range(0, epl_len, writelength):
                if offset + writelength <= epl_len:
                    datachunk = data[offset : offset + writelength]
                    self.xcvr_eeprom.write_flexible(0xA0*PAGE_LENGTH+offset+INIT_OFFSET, writelength, datachunk)
                else:
                    datachunk = data[offset : ]
                    self.xcvr_eeprom.write_flexible(0xA0*PAGE_LENGTH+offset+INIT_OFFSET, len(datachunk), datachunk)
        subtimeint = time.time()-subtime
        print('2048B write time:  %.2fs' %subtimeint)
        cmd = bytearray(b'\x01\x04\x08\x00\x04\x00\x00\x00')
        addr_byte = struct.pack('>L',addr)
        cmd += addr_byte
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return status
    # FW download complete
    def cmd0107h(self):
        cmd = bytearray(b'\x01\x07\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return status

    # Run FW image
    # mode:
    # 00h = Traffic affecting Reset to Inactive Image.
    # 01h = Attempt Hitless Reset to Inactive Image
    # 02h = Traffic affecting Reset to Running Image.
    # 03h = Attempt Hitless Reset to Running Image
    def cmd0109h(self, mode=0x01):
        cmd = bytearray(b'\x01\x09\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00')
        cmd[137-INIT_OFFSET] = mode
        cmd[138-INIT_OFFSET] = 2 # Delay to Reset 512 ms
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return status

    # Commit FW image
    def cmd010Ah(self):
        cmd = bytearray(b'\x01\x0A\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        for attemp in range(MAX_TRY):
            self.write_cdb(cmd)
            time.sleep(2)
            status = self.cdb1_chkstatus()
            if (status != 0x1):
                print('CDB1 status: Fail. CDB1 status %d' %status)
                continue
            else:
                break
        return status